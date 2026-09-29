"""A small tkinter status window for debugging the game state."""

import threading
import tkinter as tk

# Module-level variables
_root: tk.Tk | None = None
_text_widget: tk.Text | None = None  # We need a global reference to the text widget
_thread: threading.Thread | None = None


def _create_window() -> None:
    """Creates a resizable window with a scrollable and wrapping Text widget."""
    global _root, _text_widget  # Make both global

    _root = tk.Tk()
    _root.title("Game Status")
    _root.geometry("300x200")

    container = tk.Frame(_root)
    container.pack(fill="both", expand=True, padx=10, pady=10)

    scrollbar = tk.Scrollbar(container)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Assign the created widget to our global variable
    _text_widget = tk.Text(container, font=("Consolas", 12), wrap=tk.WORD, yscrollcommand=scrollbar.set)
    _text_widget.pack(side=tk.LEFT, fill="both", expand=True)

    scrollbar.config(command=_text_widget.yview)

    # Initial text
    _text_widget.insert(tk.END, "Initializing...")
    _text_widget.config(state=tk.DISABLED)

    _root.mainloop()
    # When mainloop exits, the window is gone. Clear the widget reference.
    _text_widget = None


def start() -> None:
    """Starts the status window in a non-blocking manner."""
    global _thread
    if _thread is None or not _thread.is_alive():
        _thread = threading.Thread(target=_create_window, daemon=True)
        _thread.start()


def update(text: str) -> bool:
    """Update the text displayed in the Text widget.

    This is now thread-safe and works with the Text widget.
    """
    # Check if the widget exists (i.e., the window is open)
    if _text_widget:
        try:
            # 1. Set state to NORMAL to allow editing
            _text_widget.config(state=tk.NORMAL)
            # 2. Delete all existing text (from line 1, character 0 to the end)
            _text_widget.delete("1.0", tk.END)
            # 3. Insert the new text
            _text_widget.insert(tk.END, text)
            # 4. Set state back to DISABLED to make it read-only
            _text_widget.config(state=tk.DISABLED)
            return True
        except tk.TclError:
            # This error happens if the window is closed while trying to update
            return False
    return False


def is_running() -> bool:
    """Checks if the status window's thread is currently active."""
    return _thread is not None and _thread.is_alive()
