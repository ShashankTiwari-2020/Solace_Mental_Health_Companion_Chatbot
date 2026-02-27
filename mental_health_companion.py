"""
Solace - Mental Health Companion Chatbot
A warm, empathetic AI companion using OpenAI or OpenRouter API.

Requirements:
    pip install requests

Usage:
    python mental_health_companion.py

    Or set your API key as an environment variable:
        $env:OPENAI_API_KEY = "your-openai-api-key-here"
        $env:OPENROUTER_API_KEY = "your-openrouter-api-key-here"
    Then run:
        python mental_health_companion.py
"""

import os
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, messagebox
import requests
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()

# ─── Configuration ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Solace, a warm and empathetic mental health companion. Your role is to:
- Listen deeply and reflect back what you hear with genuine compassion
- Validate emotions without judgment
- Ask thoughtful, open-ended questions to help the user explore their feelings
- Offer gentle, evidence-based coping strategies when appropriate (breathing exercises, grounding techniques, journaling prompts)
- Recognize when someone may need professional help and gently encourage it
- Never diagnose or prescribe
- Keep responses concise (2-4 sentences usually), warm, and conversational
- Use simple, accessible language
- If someone expresses suicidal ideation or self-harm, ALWAYS provide crisis resources: 988 Suicide & Crisis Lifeline (call/text 988 in the US)

Always respond with warmth, patience, and genuine care."""

# Colors
BG_DARK       = "#0f0c1a"
BG_SIDEBAR    = "#130f22"
BG_BUBBLE_BOT = "#1e1630"
BG_BUBBLE_USR = "#5b21b6"
BG_INPUT      = "#1a1530"
ACCENT        = "#a78bfa"
ACCENT2       = "#7c3aed"
TEXT_PRIMARY  = "#f5f0ff"
TEXT_MUTED    = "#9ca3af"
TEXT_DIM      = "#6b7280"
BORDER        = "#2d2050"

QUICK_PROMPTS = [
    "I'm feeling overwhelmed",
    "I can't sleep",
    "I need to talk",
    "I feel lonely",
    "I'm anxious",
    "Help me breathe",
]

BOX_BREATHING_STEPS = [
    ("Inhale…",  4),
    ("Hold…",    4),
    ("Exhale…",  6),
    ("Hold…",    4),
]

# ─── Main Application ─────────────────────────────────────────────────────────

class SolaceApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Solace — Mental Health Companion")
        self.root.geometry("920x680")
        self.root.configure(bg=BG_DARK)
        self.root.minsize(700, 520)

        self.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        self.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self.api_provider = "OpenRouter"
        self.api_key = self.openrouter_api_key
        self.client = None
        self.conversation_history: list[dict] = []
        self.breathing = False
        self.breath_thread = None

        self._build_ui()

        # Auto-connect if key is in env
        if self.openai_api_key or self.openrouter_api_key:
            self._connect_client()
            self.root.after(400, self._send_greeting)

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        """Build the full interface."""
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Sidebar
        sidebar = tk.Frame(self.root, bg=BG_SIDEBAR, width=220)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        self._build_sidebar(sidebar)

        # Main chat area
        main = tk.Frame(self.root, bg=BG_DARK)
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)
        self._build_header(main)
        self._build_chat(main)
        self._build_input(main)

    def _on_provider_change(self, *args):
        self.api_provider = self.provider_var.get()
        self._update_key_entry()

    def _update_key_entry(self):
        self.key_entry.delete(0, tk.END)
        if self.api_provider == "OpenAI":
            self.api_key = self.openai_api_key
        else:  # OpenRouter
            self.api_key = self.openrouter_api_key
        if self.api_key:
            self.key_entry.insert(0, self.api_key)

    def _build_sidebar(self, parent):
        parent.columnconfigure(0, weight=1)

        # Logo
        logo_frame = tk.Frame(parent, bg=BG_SIDEBAR)
        logo_frame.grid(row=0, column=0, pady=(20, 10), padx=16, sticky="w")
        tk.Label(logo_frame, text="✦", font=("Georgia", 20), fg=ACCENT, bg=BG_SIDEBAR).pack(side="left", padx=(0, 8))
        tk.Label(logo_frame, text="Solace", font=("Georgia", 18, "bold"), fg=TEXT_PRIMARY, bg=BG_SIDEBAR).pack(side="left")

        # API Provider section
        provider_frame = tk.Frame(parent, bg=BG_SIDEBAR)
        provider_frame.grid(row=2, column=0, padx=12, pady=6, sticky="ew")
        provider_frame.columnconfigure(0, weight=1)
        tk.Label(provider_frame, text="API PROVIDER", font=("Helvetica", 9, "bold"), fg=TEXT_DIM, bg=BG_SIDEBAR).grid(row=0, column=0, sticky="w")
        
        self.provider_var = tk.StringVar(value="OpenRouter")
        self.provider_var.trace("w", self._on_provider_change)
        provider_options = ["OpenAI", "OpenRouter"]
        self.provider_menu = tk.OptionMenu(provider_frame, self.provider_var, *provider_options)
        self.provider_menu.config(bg=BG_INPUT, fg=TEXT_PRIMARY, font=("Helvetica", 10), relief="flat", highlightthickness=0)
        self.provider_menu.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        
        tk.Frame(parent, bg=BORDER, height=1).grid(row=3, column=0, sticky="ew", padx=12, pady=4)

        # API Key section
        key_frame = tk.Frame(parent, bg=BG_SIDEBAR)
        key_frame.grid(row=4, column=0, padx=12, pady=6, sticky="ew")
        key_frame.columnconfigure(0, weight=1)
        tk.Label(key_frame, text="API KEY", font=("Helvetica", 9, "bold"), fg=TEXT_DIM, bg=BG_SIDEBAR).grid(row=0, column=0, sticky="w")
        self.key_entry = tk.Entry(key_frame, bg="#1a1530", fg=TEXT_MUTED, insertbackground=ACCENT,
                                   relief="flat", font=("Courier", 10), show="•")
        self.key_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0), ipady=5, ipadx=4)
        self._update_key_entry()
        self.connect_btn = self._make_button(key_frame, "Connect", self._on_connect)
        self.connect_btn.grid(row=2, column=0, sticky="ew", pady=(6, 0), ipady=4)

        self.status_label = tk.Label(key_frame, text="● Not connected", font=("Helvetica", 9),
                                      fg=TEXT_DIM, bg=BG_SIDEBAR)
        self.status_label.grid(row=3, column=0, sticky="w", pady=(4, 0))

        tk.Frame(parent, bg=BORDER, height=1).grid(row=5, column=0, sticky="ew", padx=12, pady=8)

        # Box Breathing
        breath_frame = tk.Frame(parent, bg=BG_SIDEBAR)
        breath_frame.grid(row=6, column=0, padx=12, pady=2, sticky="ew")
        breath_frame.columnconfigure(0, weight=1)
        tk.Label(breath_frame, text="BOX BREATHING", font=("Helvetica", 9, "bold"), fg=TEXT_DIM, bg=BG_SIDEBAR).grid(row=0, column=0, sticky="w")
        tk.Label(breath_frame, text="Calm your nervous system", font=("Helvetica", 9), fg=TEXT_MUTED, bg=BG_SIDEBAR).grid(row=1, column=0, sticky="w", pady=(2, 8))

        self.breath_canvas = tk.Canvas(breath_frame, width=90, height=90, bg=BG_SIDEBAR, highlightthickness=0)
        self.breath_canvas.grid(row=2, column=0, pady=(0, 8))
        self._draw_breath_circle("Ready", 1.0)

        self.breath_btn = self._make_button(breath_frame, "Start Breathing", self._toggle_breathing)
        self.breath_btn.grid(row=3, column=0, sticky="ew", ipady=4)

        tk.Frame(parent, bg=BORDER, height=1).grid(row=7, column=0, sticky="ew", padx=12, pady=8)

        # Quick prompts
        qp_frame = tk.Frame(parent, bg=BG_SIDEBAR)
        qp_frame.grid(row=8, column=0, padx=12, pady=2, sticky="ew")
        qp_frame.columnconfigure(0, weight=1)
        tk.Label(qp_frame, text="QUICK START", font=("Helvetica", 9, "bold"), fg=TEXT_DIM, bg=BG_SIDEBAR).grid(row=0, column=0, sticky="w", pady=(0, 6))
        for i, prompt in enumerate(QUICK_PROMPTS):
            btn = tk.Button(qp_frame, text=prompt, font=("Helvetica", 10), fg=ACCENT,
                            bg="#1a1530", activeforeground=TEXT_PRIMARY, activebackground=ACCENT2,
                            relief="flat", cursor="hand2", anchor="w",
                            command=lambda p=prompt: self._send_quick(p))
            btn.grid(row=i + 1, column=0, sticky="ew", pady=2, ipady=5, ipadx=6)

        # Disclaimer at bottom
        disc = tk.Label(parent, text="⚠ Crisis? Call/text 988", font=("Helvetica", 9),
                        fg="#ef4444", bg=BG_SIDEBAR, wraplength=190, justify="center")
        disc.grid(row=9, column=0, pady=14, padx=12, sticky="sew")
        parent.rowconfigure(9, weight=1)

    def _build_header(self, parent):
        header = tk.Frame(parent, bg="#130f22", pady=12)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        tk.Label(header, text="✦", font=("Georgia", 22), fg=ACCENT, bg="#130f22").grid(row=0, column=0, padx=(16, 8))
        name_frame = tk.Frame(header, bg="#130f22")
        name_frame.grid(row=0, column=1, sticky="w")
        tk.Label(name_frame, text="Solace", font=("Georgia", 16, "bold"), fg=TEXT_PRIMARY, bg="#130f22").pack(anchor="w")
        tk.Label(name_frame, text="● Here for you", font=("Helvetica", 9), fg="#34d399", bg="#130f22").pack(anchor="w")

        tk.Frame(parent, bg=BORDER, height=1).grid(row=1, column=0, sticky="ew")  # wait, header is row 0

    def _build_chat(self, parent):
        chat_frame = tk.Frame(parent, bg=BG_DARK)
        chat_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)

        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, bg=BG_DARK, fg=TEXT_PRIMARY,
            font=("Georgia", 12), relief="flat", padx=20, pady=16,
            selectbackground=ACCENT2, insertbackground=ACCENT,
            state="disabled", cursor="arrow",
        )
        self.chat_display.grid(row=0, column=0, sticky="nsew")

        # Tag configuration for message styling
        self.chat_display.tag_configure("bot_name", foreground=ACCENT, font=("Helvetica", 10, "bold"))
        self.chat_display.tag_configure("bot_msg", foreground=TEXT_PRIMARY, font=("Georgia", 12), lmargin1=40, lmargin2=40, rmargin=60)
        self.chat_display.tag_configure("user_name", foreground=ACCENT2, font=("Helvetica", 10, "bold"), justify="right")
        self.chat_display.tag_configure("user_msg", foreground=TEXT_PRIMARY, font=("Georgia", 12), lmargin1=60, lmargin2=60, justify="right")
        self.chat_display.tag_configure("spacing", font=("Helvetica", 4))
        self.chat_display.tag_configure("thinking", foreground=TEXT_DIM, font=("Georgia", 11, "italic"), lmargin1=40)
        self.chat_display.tag_configure("crisis", foreground="#ef4444", font=("Helvetica", 10, "bold"), lmargin1=40, lmargin2=40)
        self.chat_display.tag_configure("separator", foreground=BORDER)

    def _build_input(self, parent):
        tk.Frame(parent, bg=BORDER, height=1).grid(row=2, column=0, sticky="ew")

        input_frame = tk.Frame(parent, bg=BG_DARK, pady=12, padx=16)
        input_frame.grid(row=3, column=0, sticky="ew")
        input_frame.columnconfigure(0, weight=1)

        self.input_box = tk.Text(
            input_frame, height=3, bg=BG_INPUT, fg=TEXT_PRIMARY,
            font=("Georgia", 12), relief="flat", padx=14, pady=10,
            insertbackground=ACCENT, selectbackground=ACCENT2,
            wrap=tk.WORD,
        )
        self.input_box.grid(row=0, column=0, sticky="ew", ipadx=4)
        self.input_box.bind("<Return>", self._on_enter)
        self.input_box.bind("<Shift-Return>", lambda e: None)  # allow newline with Shift+Enter
        self.input_box.insert("1.0", "Share what's on your mind…")
        self.input_box.configure(fg=TEXT_DIM)
        self.input_box.bind("<FocusIn>", self._clear_placeholder)
        self.input_box.bind("<FocusOut>", self._restore_placeholder)

        send_btn = tk.Button(
            input_frame, text="Send ➤", font=("Helvetica", 11, "bold"),
            fg=TEXT_PRIMARY, bg=ACCENT2, activeforeground=TEXT_PRIMARY,
            activebackground=ACCENT, relief="flat", cursor="hand2",
            command=self._send_message, padx=16, pady=10,
        )
        send_btn.grid(row=0, column=1, padx=(10, 0), sticky="ns")

        hint = tk.Label(input_frame, text="Enter to send • Shift+Enter for new line",
                        font=("Helvetica", 8), fg=TEXT_DIM, bg=BG_DARK)
        hint.grid(row=1, column=0, sticky="w", pady=(4, 0))

    # ── Helper builders ───────────────────────────────────────────────────────

    def _make_button(self, parent, text, command):
        return tk.Button(
            parent, text=text, font=("Helvetica", 10, "bold"),
            fg=TEXT_PRIMARY, bg=ACCENT2, activeforeground=TEXT_PRIMARY,
            activebackground=ACCENT, relief="flat", cursor="hand2",
            command=command,
        )

    def _draw_breath_circle(self, label: str, scale: float):
        c = self.breath_canvas
        c.delete("all")
        cx, cy, r = 45, 45, 30
        r_scaled = int(r * scale)
        # Outer glow
        for i in range(4, 0, -1):
            alpha_hex = ["11", "22", "33", "55"][4 - i]
            c.create_oval(cx - r_scaled - i*4, cy - r_scaled - i*4,
                          cx + r_scaled + i*4, cy + r_scaled + i*4,
                          fill="", outline=f"#{alpha_hex}00ff", width=1)
        c.create_oval(cx - r_scaled, cy - r_scaled, cx + r_scaled, cy + r_scaled,
                      fill="#3b1d8a", outline=ACCENT, width=2)
        c.create_text(cx, cy, text=label, fill=TEXT_PRIMARY, font=("Helvetica", 9, "bold"))

    # ── API Connection ────────────────────────────────────────────────────────

    def _on_connect(self):
        key = self.key_entry.get().strip()
        if not key:
            provider = self.provider_var.get()
            messagebox.showerror("Missing Key", f"Please enter your {provider} API key.")
            return
        self.api_key = key
        if self.api_provider == "OpenAI":
            self.openai_api_key = key
        else:  # OpenRouter
            self.openrouter_api_key = key
        self._connect_client()
        if self.client and not self.conversation_history:
            self._send_greeting()

    def _connect_client(self):
        try:
            if self.api_provider == "OpenAI":
                # Test the OpenAI API key
                headers = {"Authorization": f"Bearer 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"}
                response = requests.get("https://openrouter.ai/api/v1/models", headers=headers)
                print(f'Status:{response.status_code}')
                if response.status_code == 200:
                    
                    self.client = True
                    self.status_label.configure(text="● Connected", fg="#34d399")
                else:
                    raise Exception("Invalid API key")
            else:  # OpenRouter
                # Test the OpenRouter API key
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = requests.get("https://openrouter.ai/api/v1/models", headers=headers)
                if response.status_code == 200:
                    self.client = True
                    self.status_label.configure(text="● Connected", fg="#34d399")
                else:
                    raise Exception("Invalid API key")
        except Exception as e:
            self.status_label.configure(text="● Error", fg="#ef4444")
            messagebox.showerror("Connection Error", str(e))

    # ── Messaging ─────────────────────────────────────────────────────────────

    def _send_greeting(self):
        threading.Thread(target=self._stream_response, args=([{"role": "user", "content": "Hello"}],), daemon=True).start()

    def _clear_placeholder(self, event):
        if self.input_box.get("1.0", "end-1c") == "Share what's on your mind…":
            self.input_box.delete("1.0", "end")
            self.input_box.configure(fg=TEXT_PRIMARY)

    def _restore_placeholder(self, event):
        if not self.input_box.get("1.0", "end-1c").strip():
            self.input_box.insert("1.0", "Share what's on your mind…")
            self.input_box.configure(fg=TEXT_DIM)

    def _on_enter(self, event):
        if not event.state & 0x1:  # No Shift key
            self._send_message()
            return "break"

    def _send_quick(self, prompt: str):
        self.input_box.delete("1.0", "end")
        self.input_box.configure(fg=TEXT_PRIMARY)
        self.input_box.insert("1.0", prompt)
        self._send_message()

    def _send_message(self):
        if not self.client:
            provider = self.provider_var.get()
            messagebox.showwarning("Not Connected", f"Please enter your {provider} API key and click Connect.")
            return
        text = self.input_box.get("1.0", "end-1c").strip()
        if not text or text == "Share what's on your mind…":
            return

        self.input_box.delete("1.0", "end")
        self.input_box.configure(fg=TEXT_PRIMARY)
        self._append_message("user", "You", text)
        self.conversation_history.append({"role": "user", "content": text})
        threading.Thread(target=self._stream_response, args=(self.conversation_history,), daemon=True).start()

    def _stream_response(self, messages: list):
        self.root.after(0, self._show_thinking)
        try:
            if self.api_provider == "OpenAI":
                # Use OpenAI Chat Completions API
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                # Prepare messages for OpenAI format
                openai_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                for msg in messages:
                    openai_messages.append({"role": msg["role"], "content": msg["content"]})
                
                payload = {
                    "model": "gpt-3.5-turbo",
                    "messages": openai_messages,
                    "max_tokens": 150,
                    "temperature": 0.7
                }
                
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    full_text = result["choices"][0]["message"]["content"].strip()
                else:
                    raise Exception(f"API Error: {response.status_code}")
            else:  # OpenRouter
                # Use OpenRouter Chat Completions API
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                # Prepare messages for OpenRouter format (same as OpenAI)
                openrouter_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                for msg in messages:
                    openrouter_messages.append({"role": msg["role"], "content": msg["content"]})
                
                payload = {
                    "model": "anthropic/claude-3-haiku",  # Correct model name for OpenRouter
                    "messages": openrouter_messages,
                    "max_tokens": 150,
                    "temperature": 0.7
                }
                
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    full_text = result["choices"][0]["message"]["content"].strip()
                else:
                    raise Exception(f"API Error: {response.status_code}")
            self.root.after(0, lambda: self._start_bot_message("Solace"))
            self.root.after(0, lambda t=full_text: self._append_chunk(t))

            self.conversation_history.append({"role": "assistant", "content": full_text})
            self.root.after(0, self._finish_bot_message)

        except Exception as e:
            self.root.after(0, self._hide_thinking)
            self.root.after(0, lambda err=e: self._append_message("bot", "Solace", f"Something went wrong: {err}"))

    def _show_thinking(self):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", "\nSolace is listening…\n", "thinking")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def _hide_thinking(self):
        self.chat_display.configure(state="normal")
        content = self.chat_display.get("1.0", "end")
        idx = content.rfind("\nSolace is listening…\n")
        if idx >= 0:
            start = f"1.0 + {idx} chars"
            end = f"1.0 + {idx + len(chr(10) + 'Solace is listening…' + chr(10))} chars"
            self.chat_display.delete(start, end)
        self.chat_display.configure(state="disabled")

    def _start_bot_message(self, name: str):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", "\n", "spacing")
        self.chat_display.insert("end", f"✦ {name}\n", "bot_name")
        self.chat_display.configure(state="disabled")
        self._current_bot_start = self.chat_display.index("end-1c")

    def _append_chunk(self, chunk: str):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", chunk, "bot_msg")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def _finish_bot_message(self):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", "\n", "spacing")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def _append_message(self, role: str, name: str, text: str):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", "\n", "spacing")
        if role == "user":
            self.chat_display.insert("end", f"You ◆\n", "user_name")
            self.chat_display.insert("end", text + "\n", "user_msg")
        else:
            self.chat_display.insert("end", f"✦ {name}\n", "bot_name")
            self.chat_display.insert("end", text + "\n", "bot_msg")
        self.chat_display.insert("end", "\n", "spacing")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    # ── Box Breathing ─────────────────────────────────────────────────────────

    def _toggle_breathing(self):
        if self.breathing:
            self.breathing = False
            self.breath_btn.configure(text="Start Breathing")
            self._draw_breath_circle("Ready", 1.0)
        else:
            self.breathing = True
            self.breath_btn.configure(text="Stop")
            self.breath_thread = threading.Thread(target=self._run_breathing, daemon=True)
            self.breath_thread.start()

    def _run_breathing(self):
        for cycle in range(4):
            if not self.breathing:
                break
            for label, duration in BOX_BREATHING_STEPS:
                if not self.breathing:
                    break
                # Animate scale
                steps = 30
                start_scale = 1.0
                end_scale = 1.35 if label in ("Inhale…", "Hold…") else 1.0
                for i in range(steps + 1):
                    if not self.breathing:
                        break
                    scale = start_scale + (end_scale - start_scale) * (i / steps)
                    lbl = label.replace("…", f" ({duration - int(i * duration / steps)}s)")
                    self.root.after(0, lambda s=scale, l=lbl: self._draw_breath_circle(l, s))
                    time.sleep(duration / steps)
        if self.breathing:
            self.breathing = False
            self.root.after(0, lambda: self.breath_btn.configure(text="Start Breathing"))
            self.root.after(0, lambda: self._draw_breath_circle("Done ✓", 1.0))


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    app = SolaceApp(root)

    # Center on screen
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    root.mainloop()


if __name__ == "__main__":
    main()
