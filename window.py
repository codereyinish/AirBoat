import socket
import threading
import subprocess
import base64
import time
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox

SOCKET_PATH = "/tmp/airboat.sock"
WINDOW_W = 420
WINDOW_H = 620
BG = "#ffffff"
FG = "#1a1a1a"
ACCENT = "#7c3aed"


class AirboatWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.convo_id = None
        self.convo_url = None
        root.title("AirBoat")
        root.geometry(f"{WINDOW_W}x{WINDOW_H}")
        root.configure(bg=BG)
        root.attributes("-topmost", True)

        top = tk.Frame(root, bg=BG, padx=12, pady=8)
        top.pack(fill="x")

        self.tab_btn = tk.Button(
            top,
            text=" + Add Claude tab",
            bg="#f0f0f0",
            fg=FG,
            relief="flat",
            font=("Helvetica", 11),
            cursor="hand2",
            command=self._on_tab_click
        )
        self.tab_btn.pack(side="left")

        bottom = tk.Frame(root, bg=BG, padx=12, pady=8)
        bottom.pack(fill="x", side="bottom")

        self.input = tk.Entry(
            bottom,
            bg="#f0f0f0",
            fg=FG,
            relief="flat",
            font=("Helvetica", 12)
        )
        self.input.pack(side="left", fill="x", expand=True)

        tk.Button(
            bottom,
            text="Ask",
            bg=ACCENT,
            fg="#ffffff",
            relief="flat",
            font=("Helvetica", 12, "bold"),
            cursor="hand2",
            command=self._send_prompt
        ).pack(side="left", padx=(8, 0))

        self.chat = scrolledtext.ScrolledText(
            root,
            bg=BG,
            fg=FG,
            font=("Helvetica", 12),
            relief="flat",
            wrap="word",
            state="disabled",
            padx=12,
            pady=8
        )
        self.chat.pack(fill="both", expand=True)


    def _on_tab_click(self):
        if self.convo_url:
            subprocess.run(["open", "-a", "Safari", self.convo_url])
            return

        url = simpledialog.askstring("Claude Tab", "Paste your Claude conversation URL:")
        if not url:
            return

        if "/chat/" not in url:
            messagebox.showerror("Invalid URL", "URL must contain /chat/")
            return

        self.convo_url = url
        self.convo_id = url.split("/chat/")[1].split("?")[0]
        self.tab_btn.config(text=f"claude.ai/chat/{self.convo_id[:8]}....")


    def _send_prompt(self):
        prompt = self.input.get().strip()
        if not prompt:
            return

        self.input.delete(0, tk.END)
        self._append_chat("You", prompt, ACCENT)

        b64_prompt = base64.b64encode(prompt.encode()).decode()

        insert_script = f'''
            tell application "Safari"
                repeat with w in windows
                    try
                        repeat with t in tabs of w
                            if URL of t contains "{self.convo_id}" then
                                tell t
                                    do JavaScript "
                                        var text = atob('{b64_prompt}');
                                        var el = document.querySelector('div[contenteditable]');
                                        el.focus();
                                        document.execCommand('insertText', false, text);
                                    "
                                end tell
                            end if
                        end repeat
                    end try
                end repeat
            end tell
        '''

        click_script = f'''
            tell application "Safari"
                repeat with w in windows
                    try
                        repeat with t in tabs of w
                            if URL of t contains "{self.convo_id}" then
                                tell t
                                    do JavaScript "
                                        var btn = document.querySelector('button[aria-label=\\"Send message\\"]');
                                        if (btn) btn.click();
                                    "
                                end tell
                            end if
                        end repeat
                    end try
                end repeat
            end tell
        '''

        subprocess.run(["osascript", "-e", insert_script])
        time.sleep(0.15)
        subprocess.run(["osascript", "-e", click_script])


    def _append_chat(self, sender: str, text: str, color: str) -> None:
        self.chat.configure(state="normal")
        self.chat.insert(tk.END, f"{sender}: ", f"{sender}_tag")
        self.chat.insert(tk.END, f"{text}\n\n")
        self.chat.tag_configure(f"{sender}_tag", foreground=color, font=("Helvetica", 12, "bold"))
        self.chat.configure(state="disabled")
        self.chat.see(tk.END)


    def _start_server(self):
        t = threading.Thread(target=self._accept_loop, daemon=True)
        t.start()

    def _accept_loop(self):
        import os
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as srv:
            srv.bind(SOCKET_PATH)
            srv.listen()
            while True:
                conn, _ = srv.accept()
                threading.Thread(target=self._read_client, args=(conn,), daemon=True).start()


    def _read_client(self, conn: socket.socket) -> None:
        buf = b""
        try:
            with conn:
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    if b"\x00" in buf:
                        text = buf.split(b"\x00")[0].decode("utf-8")
                        self._on_chunk(text)
                        break
        except Exception:
            pass


    def _on_chunk(self, text: str) -> None:
        if text == "__STOP__":
            return
        self.root.after(0, lambda: self._append_chat("Claude", text, FG))


if __name__ == "__main__":
    root = tk.Tk()
    app = AirboatWindow(root)
    app._start_server()
    root.mainloop()
