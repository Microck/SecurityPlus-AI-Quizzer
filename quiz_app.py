import os
import json
import requests
import time
import threading
import queue
import random
import tkinter as tk
from tkinter import ttk, messagebox

# --- Absolute Path Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
CONTENT_DIR = os.path.join(BASE_DIR, "organized_content")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

# --- Backend Logic ---

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return None, f"Config file not found at: {CONFIG_FILE}"
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    if not all(k in config for k in ["api_key", "model_name", "context_window"]):
        return None, "Config missing 'api_key', 'model_name', or 'context_window'."
    return config, None

def load_topics_data():
    topics_data = {}
    if not os.path.isdir(CONTENT_DIR):
        return None, f"Content directory not found at: {CONTENT_DIR}"
    for section_name in sorted(os.listdir(CONTENT_DIR)):
        section_path = os.path.join(CONTENT_DIR, section_name)
        if os.path.isdir(section_path):
            topics_data[section_name] = {
                topic_file.replace(".txt", "").replace("_", " "): os.path.join(
                    section_path, topic_file
                )
                for topic_file in sorted(os.listdir(section_path))
                if topic_file.endswith(".txt")
            }
    return topics_data, None

def get_detailed_system_prompt(num_questions=1, question_type="single correct answer"):
    question_count_str = (
        f"exactly {num_questions}" if num_questions > 1 else "exactly one"
    )
    output_structure = (
        'The JSON object must have a single key "questions" which contains a list...'
        if num_questions > 1
        else "The JSON object must have the structure shown below."
    )
    json_example = (
        '{\n  "questions": [\n    {\n      "question": "...",\n      "options": {...},\n      "answers": ["..."]\n    }\n  ]\n}'
        if num_questions > 1
        else '{\n  "question": "...",\n  "options": {...},\n  "answers": ["..."]\n}'
    )
    return f"""Act as an expert CompTIA exam question author. Create {question_count_str} {question_type} question(s) that mirror the style and complexity of the CompTIA Security+ 701 exam.
Your entire response, including the question, options, and answer, must be derived SOLELY from the provided context.
**Question Style Guidelines:**
1. **Scenario-Based:** Present a realistic problem a security professional might face.
2. **Application of Knowledge:** Test the application of concepts, not just definition recall.
3. **Plausible Options:** All answer choices should be plausible and relevant to the scenario.
4. **Use Acronyms Realistically:** If a term has a common acronym defined in the context (e.g., IDS, MFA, SIEM), use it where appropriate, just as a real exam would. Do not force acronyms unnaturally.
**Output Format:**
Your response MUST be a single, valid JSON object without any extra text or markdown. {output_structure} The structure must be exactly as follows: {json_example}"""

def generate_question_batch(context, num_questions, q_type, config):
    system_prompt = get_detailed_system_prompt(num_questions, q_type)
    api_key, model_name, api_url = (
        config["api_key"],
        config["model_name"],
        config["api_url"],
    )
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n---\n{context}\n---"},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    response = requests.post(api_url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    raw_content = response.json()["choices"][0]["message"]["content"]
    json_text = raw_content[raw_content.find("{") : raw_content.rfind("}") + 1]
    return json.loads(json_text).get("questions", [])

def generate_single_question(context, q_type, config):
    system_prompt = get_detailed_system_prompt(1, q_type)
    api_key, model_name, api_url = (
        config["api_key"],
        config["model_name"],
        config["api_url"],
    )
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n---\n{context}\n---"},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    response = requests.post(api_url, headers=headers, json=payload, timeout=90)
    response.raise_for_status()
    raw_content = response.json()["choices"][0]["message"]["content"]
    json_text = raw_content[raw_content.find("{") : raw_content.rfind("}") + 1]
    return json.loads(json_text)

# --- GUI Application ---

class QuizApp:
    def __init__(self, root):
        self.BG_COLOR = "#FFFFFF"
        self.TEXT_COLOR = "#333333"
        self.PRIMARY_COLOR = "#dc2626"
        self.LIGHT_GRAY = "#F3F4F6"
        self.BORDER_COLOR = "#E5E7EB"
        self.SUCCESS_COLOR = "#10B981"
        self.FONT_FAMILY = "Segoe UI"
        
        self.root = root
        self.root.title("CompTIA Quiz Generator")
        self.root.geometry("800x700")
        self.root.configure(bg=self.BG_COLOR)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.config, err = load_config()
        if err: messagebox.showerror("Configuration Error", err); self.root.quit(); return
            
        self.topics_data, err_topics = load_topics_data()
        if err_topics: messagebox.showerror("Content Error", err_topics); self.root.quit(); return

        self.questions = []
        self.user_answers = []
        self.current_question_index = 0
        self.api_queue = queue.Queue()
        
        self.setup_styles()
        self.main_frame = ttk.Frame(self.root, padding=20, style="Main.TFrame")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.setup_ui()

    def setup_styles(self):
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self.style.configure(".", background=self.BG_COLOR, foreground=self.TEXT_COLOR, font=(self.FONT_FAMILY, 10))
        self.style.configure("Main.TFrame", background=self.BG_COLOR)
        self.style.configure("TLabel", background=self.BG_COLOR, foreground=self.TEXT_COLOR, font=(self.FONT_FAMILY, 10))
        self.style.configure("Header.TLabel", font=(self.FONT_FAMILY, 18, "bold"))
        self.style.configure("Subheader.TLabel", font=(self.FONT_FAMILY, 10), foreground="#6B7280")
        self.style.configure("Bold.TLabel", font=(self.FONT_FAMILY, 10, "bold"))
        self.style.configure("Red.TButton", background=self.PRIMARY_COLOR, foreground="white", font=(self.FONT_FAMILY, 11, "bold"), borderwidth=0, padding=(10, 8))
        self.style.map("Red.TButton", background=[("active", "#b91c1c"), ("disabled", self.LIGHT_GRAY)])
        self.style.configure("Info.TButton", background=self.LIGHT_GRAY, foreground=self.TEXT_COLOR, font=(self.FONT_FAMILY, 9, "bold"), borderwidth=1, relief="solid")
        self.style.map("Info.TButton", bordercolor=[("hover", self.PRIMARY_COLOR)], foreground=[("hover", self.PRIMARY_COLOR)])
        self.style.configure("TCombobox", bordercolor=self.BORDER_COLOR, arrowsize=15)
        self.style.configure("TEntry", bordercolor=self.BORDER_COLOR, lightcolor=self.BORDER_COLOR)
        self.style.configure("TRadiobutton", background=self.BG_COLOR, font=(self.FONT_FAMILY, 10))
        self.style.configure("TCheckbutton", background=self.BG_COLOR, font=(self.FONT_FAMILY, 10))
        self.style.configure("TLabelFrame", background=self.BG_COLOR)
        self.style.configure("TLabelFrame.Label", background=self.BG_COLOR, font=(self.FONT_FAMILY, 11, "bold"))

    def setup_ui(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        ttk.Label(self.main_frame, text="CompTIA Security+ Quiz Generator", style="Header.TLabel").pack(pady=(0, 5))
        ttk.Label(self.main_frame, text="Configure your practice quiz below", style="Subheader.TLabel").pack(pady=(0, 20))
        ttk.Separator(self.main_frame).pack(fill="x", pady=10)

        controls_frame = ttk.Frame(self.main_frame, style="Main.TFrame")
        controls_frame.pack(fill="x", expand=True)
        
        form_grid = ttk.Frame(controls_frame, style="Main.TFrame")
        form_grid.pack(pady=10)

        update_cost_callback = self.root.register(self.update_cost_estimate)

        ttk.Label(form_grid, text="Section:", style="Bold.TLabel").grid(row=0, column=0, sticky="w", pady=8, padx=10)
        self.section_var = tk.StringVar()
        self.section_combo = ttk.Combobox(form_grid, textvariable=self.section_var, values=list(self.topics_data.keys()), state="readonly", width=40)
        self.section_combo.grid(row=0, column=1, sticky="ew", padx=10)
        self.section_combo.bind("<<ComboboxSelected>>", self.update_topics)

        ttk.Label(form_grid, text="Topic:", style="Bold.TLabel").grid(row=1, column=0, sticky="w", pady=8, padx=10)
        self.topic_var = tk.StringVar()
        self.topic_combo = ttk.Combobox(form_grid, textvariable=self.topic_var, state="disabled", width=40)
        self.topic_combo.grid(row=1, column=1, sticky="ew", padx=10)
        self.topic_combo.bind("<<ComboboxSelected>>", self.update_cost_estimate)

        ttk.Label(form_grid, text="Question Type:", style="Bold.TLabel").grid(row=2, column=0, sticky="w", pady=8, padx=10)
        self.q_type_var = tk.StringVar(value="single correct answer")
        self.q_type_combo = ttk.Combobox(form_grid, textvariable=self.q_type_var, values=["single correct answer", "multiple correct answers", "Mixed"], state="readonly")
        self.q_type_combo.grid(row=2, column=1, sticky="ew", padx=10)
        self.q_type_combo.bind("<<ComboboxSelected>>", self.update_cost_estimate)

        ttk.Label(form_grid, text="Generation Mode:", style="Bold.TLabel").grid(row=3, column=0, sticky="w", pady=8, padx=10)
        mode_frame = ttk.Frame(form_grid, style="Main.TFrame")
        mode_frame.grid(row=3, column=1, sticky="ew", padx=10)
        self.mode_var = tk.StringVar(value="Single Mode")
        self.mode_combo = ttk.Combobox(mode_frame, textvariable=self.mode_var, values=["Single Mode", "Batch Mode"], state="readonly")
        self.mode_combo.pack(side="left", fill="x", expand=True)
        self.mode_combo.bind("<<ComboboxSelected>>", self.update_cost_estimate)
        self.info_button = ttk.Button(mode_frame, text="?", width=3, command=self.show_mode_info, style="Info.TButton")
        self.info_button.pack(side="left", padx=(5, 0))

        ttk.Label(form_grid, text="Number of Questions:", style="Bold.TLabel").grid(row=4, column=0, sticky="w", pady=8, padx=10)
        self.num_questions_var = tk.StringVar(value="5")
        self.num_questions_entry = ttk.Entry(form_grid, textvariable=self.num_questions_var, width=10, validate="key", validatecommand=(update_cost_callback, "%P"))
        self.num_questions_entry.grid(row=4, column=1, sticky="w", padx=10)

        self.manual_pricing_var = tk.BooleanVar(value=False)
        self.manual_check = ttk.Checkbutton(form_grid, text="Use Manual Pricing (to estimate cost)", variable=self.manual_pricing_var, command=self.toggle_manual_pricing, style="TCheckbutton")
        self.manual_check.grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=(15, 5))

        self.manual_prices_frame = ttk.Frame(form_grid, style="Main.TFrame")
        self.manual_prices_frame.grid(row=6, column=0, columnspan=2, sticky="ew", padx=10)
        
        ttk.Label(self.manual_prices_frame, text="Input ($/1M tok):").pack(side="left")
        self.manual_input_price_var = tk.StringVar(value="0.0")
        self.manual_input_entry = ttk.Entry(self.manual_prices_frame, textvariable=self.manual_input_price_var, width=10)
        self.manual_input_entry.pack(side="left", padx=(5, 15))
        self.manual_input_entry.bind("<KeyRelease>", self.update_cost_estimate)

        ttk.Label(self.manual_prices_frame, text="Output ($/1M tok):").pack(side="left")
        self.manual_output_price_var = tk.StringVar(value="0.0")
        self.manual_output_entry = ttk.Entry(self.manual_prices_frame, textvariable=self.manual_output_price_var, width=10)
        self.manual_output_entry.pack(side="left", padx=5)
        self.manual_output_entry.bind("<KeyRelease>", self.update_cost_estimate)

        self.cost_label = ttk.Label(form_grid, text="Estimated Cost: N/A")
        self.cost_label.grid(row=7, column=1, sticky="w", padx=10, pady=5)

        self.generate_button = ttk.Button(self.main_frame, text="Generate Quiz", command=self.start_generation_thread, style="Red.TButton")
        self.generate_button.pack(pady=20)
        self.status_label = ttk.Label(self.main_frame, text="")
        self.status_label.pack(pady=5)

        self.load_settings()
        self.toggle_manual_pricing()

    def load_settings(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                self.section_var.set(settings.get("section", ""))
                self.update_topics() # Populate topics before setting the value
                self.topic_var.set(settings.get("topic", ""))
                self.q_type_var.set(settings.get("q_type", "single correct answer"))
                self.mode_var.set(settings.get("mode", "Single Mode"))
                self.num_questions_var.set(settings.get("num_questions", "5"))
                self.manual_pricing_var.set(settings.get("manual_pricing", False))
                self.manual_input_price_var.set(settings.get("manual_input", "0.0"))
                self.manual_output_price_var.set(settings.get("manual_output", "0.0"))
        except Exception as e:
            print(f"Could not load settings: {e}")

    def on_closing(self):
        try:
            settings = {
                "section": self.section_var.get(),
                "topic": self.topic_var.get(),
                "q_type": self.q_type_var.get(),
                "mode": self.mode_var.get(),
                "num_questions": self.num_questions_var.get(),
                "manual_pricing": self.manual_pricing_var.get(),
                "manual_input": self.manual_input_price_var.get(),
                "manual_output": self.manual_output_price_var.get(),
            }
            with open(SETTINGS_FILE, "w") as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Could not save settings: {e}")
        self.root.destroy()

    def toggle_manual_pricing(self):
        if self.manual_pricing_var.get():
            self.manual_prices_frame.grid()
            self.cost_label.grid()
        else:
            self.manual_prices_frame.grid_remove()
            self.cost_label.grid_remove()
        self.update_cost_estimate()

    def update_cost_estimate(self, *args):
        if not self.manual_pricing_var.get(): return True
        try:
            topic_name = self.topic_var.get()
            num_q_str = self.num_questions_var.get()
            if not (topic_name and num_q_str):
                self.cost_label.config(text="Estimated Cost: N/A")
                return True
            num_q = int(num_q_str)
            input_price = float(self.manual_input_price_var.get())
            output_price = float(self.manual_output_price_var.get())
            if input_price == 0 and output_price == 0:
                self.cost_label.config(text="Estimated Cost: $0.00 (Free Model)")
                return True
            section = self.section_var.get()
            topic_path = self.topics_data[section][topic_name]
            with open(topic_path, "r", encoding="utf-8") as f:
                context_tokens = len(f.read()) // 4
            prompt_tokens = len(get_detailed_system_prompt()) // 4
            output_tokens_per_q = 400
            total_input_tokens, total_output_tokens = 0, 0
            if "Batch Mode" in self.mode_var.get():
                total_input_tokens = context_tokens + prompt_tokens
                total_output_tokens = num_q * output_tokens_per_q
            else:
                total_input_tokens = num_q * (context_tokens + prompt_tokens)
                total_output_tokens = num_q * output_tokens_per_q
            input_cost = (total_input_tokens / 1_000_000) * input_price
            output_cost = (total_output_tokens / 1_000_000) * output_price
            total_cost = input_cost + output_cost
            self.cost_label.config(text=f"Estimated Cost: ${total_cost:.6f}")
        except (ValueError, KeyError):
            self.cost_label.config(text="Estimated Cost: Invalid Price")
        return True

    def show_mode_info(self):
        messagebox.showinfo(
            "Generation Mode Explained",
            "Single Mode:\n"
            "• Generates each question one by one.\n"
            "• Cost: 1 API credit PER question.\n"
            "• Quality: Tends to produce higher quality, more complex questions.\n\n"
            "Batch Mode:\n"
            "• Generates all questions in a single request.\n"
            "• Cost: 1 API credit for the ENTIRE quiz.\n"
            "• Quality: Faster, but may result in simpler questions, especially on free models.",
        )

    def update_topics(self, event=None):
        section = self.section_var.get()
        if section:
            topics = list(self.topics_data[section].keys())
            self.topic_combo["values"] = topics
            self.topic_combo.config(state="readonly")
            self.topic_var.set(topics[0] if topics else "")
            self.update_cost_estimate()

    def start_generation_thread(self):
        if not all([self.section_var.get(), self.topic_var.get(), self.num_questions_var.get()]):
            messagebox.showwarning("Input Error", "Please fill in all fields.")
            return
        try:
            num_q = int(self.num_questions_var.get())
            if num_q < 1: raise ValueError
        except ValueError:
            messagebox.showwarning("Input Error", "Number of questions must be a positive integer.")
            return
        self.generate_button.config(state="disabled")
        self.status_label.config(text="Generating... Please wait.")
        threading.Thread(target=self.generation_worker, daemon=True).start()
        self.check_api_queue()

    def generation_worker(self):
        try:
            section = self.section_var.get()
            topic_name = self.topic_var.get()
            num_questions = int(self.num_questions_var.get())
            mode = self.mode_var.get()
            q_type_selection = self.q_type_var.get()
            topic_path = self.topics_data[section][topic_name]
            with open(topic_path, "r", encoding="utf-8") as f:
                context = f.read()
            generated_questions = []
            if "Batch Mode" in mode:
                q_type_for_api = "mixed single and multiple choice" if q_type_selection == "Mixed" else q_type_selection
                generated_questions = generate_question_batch(context, num_questions, q_type_for_api, self.config)
            else:
                delay = self.config.get("request_delay_seconds", 1)
                for _ in range(num_questions):
                    q_type_for_api = random.choice(["single correct answer", "multiple correct answers"]) if q_type_selection == "Mixed" else q_type_selection
                    q = generate_single_question(context, q_type_for_api, self.config)
                    if q: generated_questions.append(q)
                    time.sleep(delay)
            self.api_queue.put(generated_questions)
        except Exception as e:
            self.api_queue.put(e)

    def check_api_queue(self):
        try:
            result = self.api_queue.get_nowait()
            self.generate_button.config(state="normal")
            self.status_label.config(text="")
            if isinstance(result, Exception):
                messagebox.showerror("API Error", f"An error occurred:\n{result}\n\nThis might be due to reaching your daily API limit.")
            elif not result:
                messagebox.showerror("Generation Error", "Failed to generate any questions.")
            else:
                self.questions = result
                self.start_quiz()
        except queue.Empty:
            self.root.after(100, self.check_api_queue)

    def start_quiz(self):
        self.user_answers = []
        self.current_question_index = 0
        self.show_question_ui()

    def show_question_ui(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        q_data = self.questions[self.current_question_index]
        q_num = self.current_question_index + 1
        is_multiple_choice = len(q_data.get("answers", [])) > 1

        ttk.Label(self.main_frame, text=f"Question {q_num} of {len(self.questions)}", style="Header.TLabel").pack(pady=10)
        ttk.Separator(self.main_frame).pack(fill="x", pady=5)
        ttk.Label(self.main_frame, text=q_data.get("question"), wraplength=700, justify="left").pack(pady=10, anchor="w")
        
        options_frame = ttk.Frame(self.main_frame, style="Main.TFrame")
        options_frame.pack(fill="x", padx=20)

        options = q_data.get("options", {})
        if is_multiple_choice:
            self.check_vars = {}
            for key, value in options.items():
                self.create_wrapped_option(options_frame, "check", key, value)
        else:
            self.answer_var = tk.StringVar()
            for key, value in options.items():
                self.create_wrapped_option(options_frame, "radio", key, value)

        ttk.Button(self.main_frame, text="Submit Answer", command=self.submit_answer, style="Red.TButton").pack(pady=20)

    def create_wrapped_option(self, parent, opt_type, key, value):
        option_frame = ttk.Frame(parent, style="Main.TFrame")
        option_frame.pack(fill="x", anchor="w", pady=2)

        if opt_type == "check":
            var = tk.BooleanVar()
            self.check_vars[key] = var
            button = ttk.Checkbutton(option_frame, variable=var)
            button.pack(side="left", anchor="n", padx=(0, 5))
        else: # radio
            button = ttk.Radiobutton(option_frame, variable=self.answer_var, value=key)
            button.pack(side="left", anchor="n", padx=(0, 5))

        label = ttk.Label(option_frame, text=f"{key}. {value}", wraplength=650, justify="left")
        label.pack(side="left", fill="x", expand=True)

        def on_click(event):
            if opt_type == "check":
                var.set(not var.get())
            else:
                self.answer_var.set(key)
        
        label.bind("<Button-1>", on_click)

    def submit_answer(self):
        q_data = self.questions[self.current_question_index]
        is_multiple_choice = len(q_data.get("answers", [])) > 1
        if is_multiple_choice:
            selected_answers = sorted([key for key, var in self.check_vars.items() if var.get()])
            if not selected_answers: messagebox.showwarning("No Answer", "Please select at least one option."); return
            self.user_answers.append(selected_answers)
        else:
            selected_answer = self.answer_var.get()
            if not selected_answer: messagebox.showwarning("No Answer", "Please select an option."); return
            self.user_answers.append([selected_answer])
        self.current_question_index += 1
        if self.current_question_index < len(self.questions):
            self.show_question_ui()
        else:
            self.show_results_ui()

    def show_results_ui(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(self.main_frame, text="Quiz Results", style="Header.TLabel").pack(pady=10, fill="x")

        summary_frame = ttk.Frame(self.main_frame, style="Main.TFrame")
        summary_frame.pack(side=tk.BOTTOM, fill="x", pady=10, padx=10)
        
        correct_count = 0
        for i, q_data in enumerate(self.questions):
            user_ans_list = self.user_answers[i]
            correct_ans_list = sorted(q_data.get("answers", []))
            if user_ans_list == correct_ans_list:
                correct_count += 1

        summary_text = f"Final Score: {correct_count} out of {len(self.questions)}"
        ttk.Label(summary_frame, text=summary_text, font=(self.FONT_FAMILY, 14, "bold")).pack()
        ttk.Button(summary_frame, text="Take Another Quiz", command=self.setup_ui, style="Red.TButton").pack(pady=10)

        results_container = ttk.Frame(self.main_frame, style="Main.TFrame")
        results_container.pack(side=tk.TOP, fill="both", expand=True)

        canvas = tk.Canvas(results_container, bg=self.BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(results_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="Main.TFrame")
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        canvas_frame_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def on_canvas_configure(event):
            canvas.itemconfig(canvas_frame_id, width=event.width)
        canvas.bind('<Configure>', on_canvas_configure)

        for i, q_data in enumerate(self.questions):
            user_ans_list = self.user_answers[i]
            correct_ans_list = sorted(q_data.get("answers", []))
            is_correct = user_ans_list == correct_ans_list
            
            status = "[+] CORRECT" if is_correct else "[-] INCORRECT"
            color = self.SUCCESS_COLOR if is_correct else self.PRIMARY_COLOR
            
            res_frame = ttk.LabelFrame(scrollable_frame, text=f"Question {i+1}: {status}")
            res_frame.pack(fill="x", expand=True, padx=10, pady=5)
            
            ttk.Label(res_frame, text=q_data.get("question"), wraplength=600, justify="left").pack(anchor="w", pady=5, padx=5)
            ttk.Label(res_frame, text=f"Your answer: {', '.join(user_ans_list)}", foreground=color).pack(anchor="w", padx=5)
            
            # --- THE FIX ---
            options = q_data.get("options", {})
            correct_answer_texts = [f"{ans}. {options.get(ans, 'N/A')}" for ans in correct_ans_list]
            full_correct_answer_str = "\n".join(correct_answer_texts)
            
            ttk.Label(res_frame, text=f"Correct answer(s):\n{full_correct_answer_str}", foreground=self.SUCCESS_COLOR, justify="left", wraplength=600).pack(anchor="w", padx=5, pady=(0, 5))

        self.root.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

if __name__ == "__main__":
    root = tk.Tk()
    app = QuizApp(root)
    root.mainloop()