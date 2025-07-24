# CompTIA Security+ Quiz Generator

![App Screenshot](https://github.com/user-attachments/assets/66d71ab0-d928-45ba-8d38-ae017ab1a2d2)

A modern, standalone desktop application designed to help you study for the **CompTIA Security+ (SY0-701)** certification exam. This tool uses the power of large language models via the OpenRouter API to generate realistic, scenario-based practice questions directly from your personal study notes.

---

## About The Project

Studying for certifications often involves re-reading notes and trying to anticipate exam questions. This tool automates that process by acting as your personal exam author. You provide the study material as simple `.txt` files, and the application generates a custom quiz, helping you test your knowledge and application of the concepts you've learned.

---

## Features

- **AI-Powered Question Generation:** Leverages the OpenRouter API to create high-quality, unique practice questions.
- **Modern Desktop GUI:** A clean, minimalistic interface built with Python's native Tkinter library. No web browser or complex setup needed.
- **Highly Customizable Quizzes:**
  - Select specific sections and topics.
  - Choose the number of questions.
  - Generate **single-answer**, **multiple-answer**, or a **mixed** set of questions.
- **Flexible Generation Modes:**
  - **Single Mode:** Generates questions one by one for the highest quality and complexity.
  - **Batch Mode:** Generates all questions in a single, faster API call.
- **Optional Cost Estimation:** Manually input your model's pricing to see an estimated cost before generating a quiz.
- **Interactive Quiz Interface:** Answer questions and receive a detailed, scrollable results summary with your score.

---

## Preparing Your Study Materials

This application generates quizzes by reading the content from `.txt` files that you provide. For the best results, your study material should be well-organized.

- The application looks for your notes inside the `organized_content` folder.
- Each sub-folder within `organized_content` is treated as a separate section or topic for your quizzes.
- To acquire content for these files, you can use your own detailed notes or find publicly available educational resources.
- For example, many online educational videos include transcripts that you can download or copy. You can save this text into `.txt` files and place them in the appropriate section folders.
- **Note:** The quality and accuracy of your generated quiz questions will directly depend on the quality of the text you provide.

---

## Getting Started

Follow these steps to get the application running on your local machine.

### Prerequisites

- Python 3.8 or newer. You can download it from [python.org](https://www.python.org/).
- An API key from [OpenRouter.ai](https://openrouter.ai/).

### Installation

1. **Clone the repository:**
    ```sh
    git clone https://github.com/Microck/secplus-ai-quizzer.git
    cd secplus-ai-quizzer
    ```

2. **Install Python dependencies:**
    This project requires the `requests` library.
    ```sh
    pip install requests
    ```

3. **Set up your content:**
    - Ensure you have an `organized_content` folder in the project directory.
    - Inside `organized_content`, create sub-folders for each topic (e.g., `1.1_Social_Engineering`).
    - Place your study notes as `.txt` files inside these topic folders.

4. **Configure the application:**
    - Open `config.json` and fill in your details:
        ```json
        {
          "api_key": "YOUR_OPENROUTER_API_KEY_HERE",
          "model_name": "moonshotai/kimi-k2:free",
          "context_window": 66000,
          "request_delay_seconds": 2
        }
        ```
    - `api_key`: Your key from OpenRouter.
    - `model_name`: The model you wish to use.
    - `context_window`: The context window of your chosen model.
    - `request_delay_seconds`: A delay (in seconds) between API calls in "Single Mode" to avoid rate-limiting. `2` is a safe default for free models.

---

## Usage

With your content and configuration in place, simply run the application from your terminal:

```sh
python quiz_app.py
```

The desktop application window will launch, and you can start generating quizzes.

---

## License

Distributed under the MIT License. See `LICENSE` file for more information.

---

## Acknowledgments

- **OpenRouter.ai** for providing access to a wide variety of language models.