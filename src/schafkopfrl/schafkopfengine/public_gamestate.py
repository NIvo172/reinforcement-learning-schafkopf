"""Public game state information known by all players."""

# contains information about the game that is known by all players
import csv
import datetime
from pathlib import Path

from schafkopfrl.schafkopfengine.cards import Card, Deck
from schafkopfrl.schafkopfengine.players.player import Player
from schafkopfrl.schafkopfengine.rules.rules import Rules, Sauspiel
from schafkopfrl.schafkopfengine.utils.debug import start, update
from schafkopfrl.schafkopfengine.utils.enums import Color, Game, Rank, Team
from schafkopfrl.utils.log import get_logger
from schafkopfrl.utils.safe_file import append_to_log

logger = get_logger("PublicGameState")

DEBUG = False


class PublicGameState:
    """The public observable state of a Schafkopf game."""

    # Attribute types, so mypy can resolve them regardless of source order of the resetting methods.
    players: list[Player]
    dealer: Player
    deck: Deck
    trick_number: int
    trick_owner: list[Player]
    trick_cards: list[list[Card]]
    trick_points: list[int]
    # Owns the current trick; reset to [] after each trick.
    trick_current_owner: Player | list[Player]
    trick_current_highest_card: Card | None
    trick_current_cards: list[Card]
    trick_current_points: int
    current_player: Player
    current_played_card: Card
    trumps_left: list[Card] | None
    trumps_left_int: int | None
    trumps_left_weighted: int | None
    trumps_played: list[Card]
    scores: dict[Player, int]
    scores_team: list[int]
    points_left: int
    payout: list[int]
    cards_played: list[Card]
    cards_left: list[Card]
    cards_left_int: int
    rufsau_played: bool
    colors_left: dict[Color, int]
    colors_count: dict[Color, int]
    played_cards_player: dict[Player, list[Card]]
    trumps_left_player: dict[Player, bool]
    colors_left_player: dict[Player, dict[Color, bool]]
    _game_sau: Card | None
    playing_order: list[Player] | None
    calling_player: Player | None
    gametype: Rules | None
    team: list[Team]
    contra: bool
    retour: bool
    contra_player: Player | None
    retour_player: Player | None

    def __init__(
        self,
        players: list[Player],
        starting_pos: int,
    ) -> None:
        """Create a public game state for the given players.

        Args:
            players: The four players of the game.
            starting_pos: The position of the initial dealer in players.
        """
        self.players = players
        self.dealer = self.players[starting_pos]
        self.deck = Deck()
        self._attach_gamestate_to_player()
        if DEBUG:
            start()
            self.state = ""
        # TODO: This is somehow complex, for not so many
        # occations.
        # self.davongelaufen = False

    def _attach_gamestate_to_player(self) -> None:
        for idx, player in enumerate(self.players):
            player.add_gamestate(self)
            player._seat = idx

    def start_game(self, seed: int | None = None) -> Player:
        """Reset to the default state and start a new game.

        Args:
            seed: Optional seed used for shuffling the deck.
        """
        self._reset_to_default_state()
        assert self.playing_order is not None  # noqa: S101 Internal invariant debug check.
        self._update_playing_sequence()

        if seed is not None:
            self.deck.deal_cards(self.players, seed=seed)
        else:
            self.deck.deal_cards(self.players)

        self._search_game()
        assert self.gametype is not None  # noqa: S101 Internal invariant debug check.
        self.deck.adjust_cards(self.gametype)
        self._set_trumps()
        for player in self.players:
            player.found_game_update()

        self._contra_retour()

        return self.playing_order[0]

    def _update_playing_sequence(self) -> None:
        """Set the playing sequence for a trick.

        The sequence is set, if its the first trick the player after the dealer starts, if its after the start the last
        trick owner starts.
        """
        if self.trick_number > 0:
            starting_pos = self.players.index(self.trick_owner[-1])
        else:
            starting_pos = self.players.index(self.dealer) + 1

        self.playing_order = self.players[starting_pos:] + self.players[:starting_pos]

    def _search_game(self) -> None:
        """Search for a game, then set the gametype."""
        assert self.playing_order is not None  # noqa: S101 Internal invariant debug check.

        gametype = Game.RAMSCH
        gamecolor = Color.HERZ
        game_player = None

        for player in self.playing_order:
            choosen_gametype, choosen_color = player.choose_gametype()
            if choosen_gametype > gametype:
                gametype = choosen_gametype
                gamecolor = choosen_color
                game_player = player

        self.gametype = Rules.create(gametype, gamecolor)
        if gametype == Game.SAUSPIEL:
            # self._game_sau = [card for card in self.deck.cards if ((card.rank == Rank.ACE) and (card.color == gamecolor))][0]

            self._game_sau = [card for card in self.deck._cards_category[Rank.ACE] if (card.color == gamecolor)][0]  # noqa: RUF015

        self.calling_player = game_player

    def _contra_retour(self) -> None:
        # TODO: Implement the Information given by someone calling Contra.
        # This should set the team_member attribute of the class.
        if self.game_id == Game.RAMSCH:
            return
        for player in self.players:
            if player.team == Team.NONCALLINGTEAM:
                self.contra = player.contra()

                if self.contra:
                    self.contra_player = player
                    break

        if self.contra:
            for player in self.players:
                if player.team == Team.CALLINGTEAM:
                    self.retour = player.retour()
                    if self.retour:
                        self.retour_player = player
                        break

    def _set_trumps(self) -> None:
        self.trumps_left = self.deck.trumps.copy()
        self.trumps_left_int = len(self.trumps_left)
        self.trumps_left_weighted = self._calc_weighted_trumps()

        for card in self.trumps_left:
            self.colors_left[card.color] -= 1

    def player_turn(self, player: Player, action: int | None = None) -> Player:
        """Let a player play a card.

        Args:
            player: The player that plays the card.
            action: The action index for agents. Defaults to None.
        """
        assert self.playing_order is not None  # noqa: S101 Internal invariant debug check.

        self.current_player = player
        self.current_played_card = (
            self.current_player.play_card(action) if action is not None else self.current_player.play_card()
        )

        self._trick_partial()

        # This sets the player for the next turn.
        if self._is_end_trick():
            self._calculate_globale_obs(trick_completed=True)
            self._reset_trick()

            self._update_playing_sequence()
            nxt_player = self.playing_order[0]

        else:
            self._calculate_globale_obs(trick_completed=False)

            # Problem when wrapping arround the last player.
            current_player_idx = self.playing_order.index(self.current_player)
            nxt_player = self.playing_order[current_player_idx + 1] if current_player_idx != 3 else self.playing_order[0]

        return nxt_player

    def _trick_partial(self) -> None:
        if self._first_card():
            self.trick_current_highest_card = self.current_played_card
            self.trick_current_owner = self.current_player

        else:
            assert self.trick_current_highest_card is not None  # noqa: S101 Internal invariant debug check.
            if self.trick_current_highest_card < self.current_played_card:
                self.trick_current_highest_card = self.current_played_card
                self.trick_current_owner = self.current_player

        self.trick_current_cards.append(self.current_played_card)
        self.trick_current_points += self.current_played_card.score

    def _first_card(self) -> bool:
        return len(self.trick_current_cards) == 0

    def _is_end_trick(self) -> bool:
        return len(self.trick_current_cards) == 4

    def _calc_weighted_trumps(self) -> int:
        assert self.trumps_left is not None  # noqa: S101 Internal invariant debug check.
        return sum(int(card.rank) + int(card.color) for card in self.trumps_left)

    def _calculate_globale_obs(self, trick_completed: bool) -> None:
        # General card observation
        self.cards_played.append(self.current_played_card)
        self.played_cards_player[self.current_player].append(self.current_played_card)
        self.cards_left.remove(self.current_played_card)
        self.cards_left_int -= 1

        # Handle specific card observation
        if self.current_played_card.is_trump:
            assert self.trumps_left is not None  # noqa: S101 Internal invariant debug check.
            assert self.trumps_left_int is not None  # noqa: S101 Internal invariant debug check.
            self.trumps_left.remove(self.current_played_card)
            self.trumps_left_int -= 1
            self.trumps_played.append(self.current_played_card)
            self.trumps_left_weighted = self._calc_weighted_trumps()
        else:
            # Remove color left counter
            self.colors_left[self.current_played_card.color] -= 1
            # Count colors led
            if len(self.trick_current_cards) == 1:
                self.colors_count[self.current_played_card.color] += 1

        # Handle teams
        if not self.rufsau_played and self.current_played_card == self.game_sau:
            self.rufsau_played = True
            self._form_sauspiel_teams(partner_player=self.current_player)

        # Handle completed trick.
        if trick_completed:
            # Invariant: a completed trick always has a player owner on a set team.
            assert isinstance(self.trick_current_owner, Player)  # noqa: S101 Internal invariant debug check.
            assert self.trick_current_owner.team is not None  # noqa: S101 Internal invariant debug check.

            # Trick eval.
            self.trick_number += 1
            self.trick_owner.append(self.trick_current_owner)
            self.trick_cards.append(self.trick_current_cards)
            self.trick_points.append(self.trick_current_points)

            # Score handling
            self.scores[self.trick_current_owner] += self.trick_current_points
            self.points_left -= self.trick_current_points
            self.scores_team[self.trick_current_owner.team] += self.trick_current_points

        # DEBUG
        if DEBUG:
            for whatever in dir(self):
                if whatever.startswith("__"):
                    continue
                logger.info(whatever)
            for attribute, value in vars(self).items():
                if attribute == "state":
                    continue
                if isinstance(value, dict):
                    self.state += f"{attribute}:\n"
                    v = ""

                    for key, val in value.items():
                        if isinstance(val, dict):
                            v += f"\t{key}:\n"
                            for key2, val2 in val.items():
                                v += f"\t\t{key2}\n\t\t\t"
                                v += f"{val2}\n"

                            else:
                                v += f"\t{key}:\n\t\t{val}\n"
                        self.state += v

                elif isinstance(value, list):
                    self.state += f"{attribute}:\n"
                    v = "\t"
                    for idx, element in enumerate(value, start=1):
                        if idx == 0:
                            v += f"{element}"
                        if idx % 2 == 0 and idx != 0:
                            v += f" {element}\n\t"
                        else:
                            v += f"{element}"
                    self.state += v + "\n"

                else:
                    self.state += f"{attribute}:\n {value}\n"

            self.state += "----------\n"
            update(self.state)

    def _form_sauspiel_teams(self, partner_player: Player) -> None:
        """Form the two teams in a Sauspiel once the called ace is played.

        This is called once per game.

        Args:
            partner_player: The partner of the calling player.
        """
        caller_team = [self.calling_player, partner_player]
        opponent_team = [p for p in self.players if p not in caller_team]

        # Invariant: a Sauspiel exists only once a calling player was found.
        assert self.calling_player is not None  # noqa: S101 Internal invariant debug check.

        # Only need to set for calling player, partner_player knows.
        self.calling_player.teammember = partner_player
        # partner_player.teammember = self.calling_player

        for p in opponent_team:
            for p2 in opponent_team:
                if p != p2:
                    p.teammember = p2

    ##############
    ### Things ###
    ##############

    @property
    def game_id(self) -> Game:
        """The id of the currently played game type."""
        assert self.gametype is not None  # noqa: S101 Internal invariant debug check.
        return self.gametype.gameid

    @property
    def game_sau(self) -> Card | None:
        """The searched ace of a Sauspiel, or None for other game types."""
        assert self.gametype is not None  # noqa: S101 Internal invariant debug check.
        if self.gametype.gameid == Game.SAUSPIEL:
            return self._game_sau
        return None

    @property
    def game_color(self) -> Color:
        """The trump color of the currently played game type."""
        assert self.gametype is not None  # noqa: S101 Internal invariant debug check.
        if isinstance(self.gametype, Sauspiel):
            return self.gametype.searched_color
        return self.gametype.trump_color

    ########################
    ### Evaluation Logic ###
    ########################

    def evaluate(self, log: bool = False) -> None:
        """Evaluate a finished game and compute the payouts for all players."""
        assert self.gametype is not None  # noqa: S101 Internal invariant debug check.

        payout = 0
        amount_tricks = [0, 0]

        for player in self.trick_owner:
            assert player.team is not None  # noqa: S101 Internal invariant debug check.
            amount_tricks[player.team] += 1

        if self.scores_team[Team.CALLINGTEAM] >= self.gametype.winning_threshold:
            payout += self.gametype.reward
            payout += self.gametype.reward_schneider_win(
                self.scores_team[Team.CALLINGTEAM], amount_tricks[Team.NONCALLINGTEAM]
            )
            payout += self.gametype.reward_laufende * self._check_laufende()

        if self.scores_team[Team.CALLINGTEAM] < self.gametype.winning_threshold:
            payout -= self.gametype.reward
            payout -= self.gametype.reward_schneider_loss(
                self.scores_team[Team.CALLINGTEAM], amount_tricks[Team.CALLINGTEAM]
            )
            payout -= self.gametype.reward_laufende * self._check_laufende()

        self.payout = [payout if player.team == Team.CALLINGTEAM else -payout for player in self.players]

    def _check_laufende(self) -> int:
        assert self.gametype is not None  # noqa: S101 Internal invariant debug check.

        team_player_cards = []
        team_nonplayer_cards = []
        for player in self.players:
            if player.team == Team.CALLINGTEAM:
                team_player_cards += self.played_cards_player[player]
            if player.team == Team.NONCALLINGTEAM:
                team_nonplayer_cards += self.played_cards_player[player]

        team_player_cards = sorted(
            team_player_cards, key=lambda card: (card.is_trump, card.rank, card.color), reverse=True
        )

        amount_laufender = 0

        for laufender in self.deck.trumps:
            if laufender not in team_player_cards:
                break
            amount_laufender += 1

        # Only if the other team has no laufende then
        # we check for laufende in the other team.
        if amount_laufender == 0:
            team_nonplayer_cards = sorted(
                team_nonplayer_cards, key=lambda card: (card.is_trump, card.rank, card.color), reverse=True
            )
            for laufender in self.deck.trumps:
                if laufender not in team_nonplayer_cards:
                    break
                amount_laufender += 1

        return amount_laufender if amount_laufender >= self.gametype.min_laufende else 0

    ###################
    ### Reset Logic ###
    ###################

    def _reset_trick(self) -> None:
        # Current Trick
        self.trick_current_owner = []
        self.trick_current_cards = []
        self.trick_current_points = 0
        self.trick_current_highest_card = None

    def _reset_tricks(self) -> None:
        self._reset_trick()
        self.trick_number = 0
        self.trick_owner = []
        self.trick_cards = []
        self.trick_points = []

    def _reset_trumps(self) -> None:
        self.trumps_left = None  # len of this is amount of trumps played
        self.trumps_left_int = None
        self.trumps_played = []
        self.trumps_left_weighted = None

    def _reset_scores(self) -> None:
        self.scores = dict.fromkeys(self.players, 0)
        self.scores_team = [0, 0]
        self.points_left = 120
        self.payout = []

    def _reset_to_first_turn(self) -> None:
        self._reset_tricks()
        self._reset_trumps()
        self._reset_scores()

        # cards are weighted by the points left
        self.cards_played = []
        self.cards_left = self.deck.cards.copy()
        self.cards_left_int = 32
        self.rufsau_played = False

        self.colors_left = {color: 8 for color in Color if color}

        self.colors_count = {color: 0 for color in Color if color}

        self.played_cards_player = {player: [] for player in self.players}

        # This is set in the `_allowed_cards` method in the player class.
        self.trumps_left_player = dict.fromkeys(self.players, True)
        self.colors_left_player = {player: {color: True for color in Color if color} for player in self.players}

    def _reset_to_gamesearch(self) -> None:
        """Reset the state set by the game search."""
        self._reset_to_first_turn()
        self.playing_order = None
        self.calling_player = None
        self.gametype = None
        self.team = []
        self.contra = False
        self.retour = False
        self.contra_player = None
        self.retour_player = None

    def _reset_to_default_state(self) -> None:
        """Set all the default values of a public game state class (reset)."""
        self.deck.reset_deck()

        for player in self.players:
            player._reset()

        self._reset_to_gamesearch()
        self._update_playing_sequence()

    ###########
    ### Log ###
    ###########

    def log_event_to_csv(self, event: dict[str, object], filename: Path | None = None) -> Path:
        """Append a single event (a dict of key→value) to a CSV.

        If filename is None, uses game_logs.csv in the same folder as this file; otherwise uses the given filename (or
        path-like). Creates the file (and writes header) if it does not yet exist. Returns the Path used.
        """
        # Determine default path: <this_module_folder>/game_logs.csv
        if filename is None:
            filename = Path(__file__).parent.parent.parent.parent / "reports" / "arena" / "arena_default.csv"
        else:
            filename = Path(__file__).parent.parent.parent.parent / "reports" / "arena" / filename

        # Ensure parent directory exists
        filename.parent.mkdir(parents=True, exist_ok=True)

        # Consistent ordering of columns
        fieldnames = list(event.keys())

        # Detect if we need to write header
        file_exists = filename.is_file()

        # Open and append
        with filename.open(mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(event)

        return filename

    def _save_game(self) -> None:
        def format_tricks(player_tricks: dict[Player, list[Card]]) -> str:
            lines = []

            # Header
            header = " | ".join(str(pid) for pid in player_tricks)
            lines.append(header)
            lines.append("-" * len(header))

            # Body (always 8 tricks, players sorted)
            for i in range(8):
                row = [str(player_tricks[pid][i]) for pid in player_tricks]
                lines.append(" | ".join(row))

            return "\n".join(lines)

        # Invariants: _save_game is only called after a complete game.
        assert self.gametype is not None  # noqa: S101 Internal invariant debug check.
        assert self.calling_player is not None  # noqa: S101 Internal invariant debug check.

        game_log = f"GAME: {datetime.datetime.now(datetime.UTC):%Y%m%d_%H%M%S}\n"
        game_log += f"SPIELER: {self.calling_player} (FIRST: {self.dealer.id + 1})\nGAMETYPE: {self.gametype.gamename}\n"
        if isinstance(self.gametype, Sauspiel):
            game_log += f"RUFFARBE: {self.gametype.searched_color.name}\n"
        else:
            game_log += "\n"
        game_log += f"TEAM: {[p.value for p in self.team]}\n"
        game_log += f"TRICK_WIeNER:\n{[owner.id for owner in self.trick_owner]}\n"
        game_log += f"TRICK_Points:\n{self.trick_points}\n"
        game_log += f"PAYOUT:\n{self.payout}\n"
        game_log += "TRICKS:\n" + "\n".join(", ".join(str(card) for card in trick) for trick in self.trick_cards) + "\n"
        game_log += "TRICK_BY_PLAYER:\n" + format_tricks(self.played_cards_player) + "\n"

        game_log += f"{self.players[0]}: {sorted(self.played_cards_player[self.players[0]], key=lambda card: (card.is_trump, card.rank, card.color), reverse=True)}\n"
        game_log += f"{self.players[1]}: {sorted(self.played_cards_player[self.players[1]], key=lambda card: (card.is_trump, card.rank, card.color), reverse=True)}\n"
        game_log += f"{self.players[2]}: {sorted(self.played_cards_player[self.players[2]], key=lambda card: (card.is_trump, card.rank, card.color), reverse=True)}\n"
        game_log += f"{self.players[3]}: {sorted(self.played_cards_player[self.players[3]], key=lambda card: (card.is_trump, card.rank, card.color), reverse=True)}\n"
        game_log += "\n------------------------------------------------------------\n"
        append_to_log("reports/games/game.log", game_log)

    def log_init(self) -> None:
        """Log the initial game state."""
        msg = (
            "### INIT GAMESTATE ###\n"
            + f"Players: {list(self.players)}\n"
            + f"Dealer ID: {self.dealer}\n"
            + f"Deck Instance: {id(self.deck)}\n"
            + f"Playing Order: {self.playing_order}\n"
            + "####################\n"
        )
        logger.info(msg)

    def log_gamesearch(self) -> None:
        """Log the result of the game search."""
        msg = (
            "### FOUND GAME ###\n"
            f"Player ID:\n{self.calling_player}\n"
            f"Game ID:\n{self.game_id.name}\n"
            f"Game Color:\n{self.game_color.name}\n"
            f"Team:\n{self.team}\n"
            f"Contra:\n{self.contra}\n"
            f"Retour:\n{self.retour}\n"
            f"Contra Player ID:\n{self.contra_player}\n"
            f"Retour Player ID:\n{self.retour_player}\n"
            f"Team Member by Player:\n{[player.teammember for player in self.players]}\n"
            "####################"
        )
        logger.info(msg)
        # print(msg)

    def log_trick(self, verbose: bool = False) -> None:
        """Log a completed trick."""
        msg = (
            "### COMPLETE TRICK ###\n"
            + f"Trick Count:\n{self.trick_number}\n"
            + f"Trick Owner:\n{self.trick_owner[-1]}\n"
            + f"Trick Cards:\n{self.trick_cards[-1]}\n"
            + f"Trick Points:\n{self.trick_points[-1]}\n"
            # + (
            #    f'Played Cards per Player:\n{", \n".join(f"{player}: {cards[-1]}" for player, cards in self.played_cards_player.items())}\n'
            #    if verbose
            #    else ''
            # )
            + (f"Played Cards:\n{self.cards_played}\n" if verbose else "")
            + (f"Cards Left:\n{self.cards_left}\n" if verbose else "")
            + "\n####################\n"
        )
        logger.info(msg)
        # print(msg)

    def log_current_trick(self, verbose: bool = False) -> None:
        """Log the currently played, incomplete trick."""
        msg = (
            "### CURRENT TRICK ###\n"
            f"Current Trick Owner:\n{self.trick_current_owner}\n"
            f"Current Trick Points:\n{self.trick_current_points}\n"
            f"Current Trick Winning Card:\n{self.trick_current_highest_card}\n"
            f"Current Trick Cards:\n{self.trick_current_cards}\n"
            "####################\n"
        )
        logger.info(msg)
        # print(msg)

    def log_trumps(self) -> None:
        """Log the remaining and played trumps."""
        msg = (
            "### TRUMPS ###\n"
            + f"Trumps Left:\n{self.trumps_left}\n"
            + f"Trumps Left Int:\n{self.trumps_left_int}\n"
            + f"Trumps Played:\n{self.trumps_played}\n"
            + f"Trumps Weighted:\n{self.trumps_left_weighted}\n"
            + "####################\n"
        )
        logger.info(msg)

    def log_scores(self) -> None:
        """Log the current scores."""
        msg = (
            "### SCORES ###\n"
            + f"Score:\n{self.scores}\n"
            + f"Points Left:\n{self.points_left}\n"
            + f"Team Score:\n{self.scores_team}\n"
            + "####################\n"
        )
        logger.info(msg)
        # print(msg)

    def log_others(self) -> None:
        """Log other game state information."""
        msg = "### OTHERS ###\n" + f"Rufsau Gespiel:\n{self.rufsau_played}\n" + "\n" + "####################\n"
        logger.info(msg)

    def __repr__(self) -> str:  # noqa: D105 Docstring for repr excluded by convention.
        #        dealer = f"Dealer ID: {self.dealer}\n"
        #        first_player = f"First Player ID:{self.starting_player}"
        #        game_type = f"GameType: {self.gametype}\n"
        #        player = f"Player ID: {self.calling_player}\n"
        #        gametype = f"Game: {self.game_id}{self.gametype.trump_color}\n"
        #        contra = f"Contra: {self.contra}\n"
        #        retour = f"Retour: {self.retour}\n"
        #        playing_order = f"Playing Order: {self.playing_order}"

        return ", \n".join(f"{key}: {value}" for key, value in vars(self).items())
