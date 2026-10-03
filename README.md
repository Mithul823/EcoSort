# ♻️ EcoSort AI

EcoSort uses a waste photo to identify items, classify them, and explain disposal. You can ask follow-up questions, generate a report, download it, and send it by email.

## How it works

Image upload → Gemini analysis → validated JSON → Python calculations → chat → report → download or email

Gemini identifies items and suggests disposal methods. Python counts categories and calculates:

`Recyclability score = recyclable items / total detected items × 100`

The score measures item count, not weight. AI suggestions can be wrong, and local recycling rules vary.

## Run the project

The existing virtual environment is `.ecosort`:

```bash
cd ~/Desktop/ecosort
source .ecosort/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

For a fresh checkout, create the environment first with `python3 -m venv .ecosort`.

Keep your existing `.env`. If starting fresh, copy `.env.example` to `.env` and fill in your own settings.

```dotenv
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-3.5-flash-lite
```

The default model is retained from the original project. Availability has not been verified against your account. Run `python list_model.py` to list available models, then set GEMINI_MODEL to one that supports image input and structured output.

## Using EcoSort

1. Upload a JPG or PNG under 10 MB and 20 million pixels.
2. Click **Analyze Waste**.
3. Review the detected items, category summary, and score.
4. Ask a question, such as “Which item is hazardous?”
5. Click **Generate report** and review the preview.
6. Click **Download report** to save it as a text file, or enter a recipient and click **Send EcoSort Report** in the **Your report** tab.

Changing or removing the image clears results, chat, and report. A successful new analysis clears the previous conversation. Chat stays in the current Streamlit session; it is not saved to a database. Gemini receives the analysis and the most recent 20 chat messages. The report includes the full conversation from this session. New chat answers invalidate the old report so you can regenerate it.

## Gmail email setup

Add these settings to your existing `.env` (keep your Gemini key):

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=yourname@gmail.com
SMTP_PASSWORD=your_google_app_password
SMTP_FROM=yourname@gmail.com
```

Enable Google 2-Step Verification, then create an app password named EcoSort at [Google App passwords](https://myaccount.google.com/apppasswords). Use that password without spaces. SMTP_USERNAME is your full Gmail address. Restart Streamlit after changing `.env`.

The app sends the displayed report and chat transcript as the email body, without the uploaded photo. Sending happens only when you click the send button. A success message means the mail server accepted it; inbox delivery still needs checking. Failed sends are not automatically retried. Check your inbox before retrying an uncertain delivery. Duplicate submissions of the same report to the same address are blocked during the current session.

For hosted deployment, add these same SMTP values to Streamlit secrets as quoted TOML strings. Confirm outbound SMTP is supported by the host. Keep passwords out of Git. Before unrestricted public access, add shared email rate limits and access controls.

## Project files

- `app.py`: upload, results, chat, and report controls
- `gemini_service.py`: Gemini requests, retries, structured output, and chat
- `prompt.py`: image and chatbot prompts
- `waste_utils.py`: validation, categories, and score
- `report_service.py`: report text built from results and conversation
- `email_service.py`: recipient validation and encrypted SMTP delivery
- `settings.py`: environment and Streamlit secrets
- `list_model.py`: available model listing
- `tests/test_ecosort.py`: offline service checks

The five categories are Recyclable, Organic, E-Waste, Hazardous, and General Waste.

## Errors and limits

Temporary Gemini errors and connection failures retry up to three total attempts, with a 20-second timeout per request. Invalid credentials, unavailable models, incomplete JSON, and invalid images show readable messages.

Reports are generated in Python without another Gemini call. They preserve chat advice as a transcript rather than generating a new AI summary.

This is a workshop application. Before opening it to unrestricted public traffic, add access controls and shared rate limits for paid AI requests.

## Tests and current status

```bash
python -m unittest discover -s tests -v
```

Verified locally: offline service tests, including simulated email delivery, plus Streamlit checks for startup, result display, report generation, and clearing results when the photo changes.

Still unverified: live Gemini image/chat responses, model access, actual inbox delivery, and hosted deployment. Automated API and SMTP tests use simulated responses.

## Deploy on Streamlit Community Cloud

1. Push the project to your GitHub repository. Keep `.env`, virtual environments, and `.streamlit/secrets.toml` out of Git.
2. Create an app in Streamlit Community Cloud and select `app.py` as the entrypoint.
3. Add configuration in the app's Secrets settings using TOML:

```toml
GEMINI_API_KEY = "your_key"
GEMINI_MODEL = "your_available_model"
```

4. Deploy and test image analysis, follow-up chat, report download, and email delivery.

References: [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output), [Streamlit deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), and [Streamlit secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).
