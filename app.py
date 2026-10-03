import hashlib
import logging

import streamlit as st

from conversation import start_conversation, combined_analysis, record_analysis, has_conversation
from email_service import EmailError, send_report, valid_email
from gemini_service import (
    EcoSortError, create_client, analyze_waste_image, answer_question, summarize_conversation,
)
from image_utils import prepare_image
from report_service import generate_report
from waste_utils import count_categories, calculate_recyclability_score

st.set_page_config(page_title="EcoSort AI", page_icon="♻️", layout="wide")


@st.cache_resource(scope="session", on_release=lambda client: client.close())
def get_gemini_client():
    return create_client()


def show_unexpected_error():
    logging.getLogger(__name__).warning("An EcoSort operation failed unexpectedly.")
    st.error("Something went wrong. Please try again or check the app configuration.")


def analyze_photo(photo_bytes):
    image = prepare_image(photo_bytes)
    with st.spinner("Analyzing your photo. Busy requests may take about a minute…"):
        data = analyze_waste_image(get_gemini_client(), image)
    record_analysis(st.session_state, photo_bytes, image, data)


def build_report():
    data = combined_analysis(st.session_state)
    summary = summarize_conversation(get_gemini_client(), data, st.session_state.messages)
    return generate_report(data, st.session_state.messages, summary, st.session_state.name)


if not st.session_state.get("onboarded"):
    st.title("♻️ Welcome to EcoSort")
    st.write("Sort smarter. Waste less. Get a personal report by email.")
    with st.form("onboarding"):
        name = st.text_input("Your name", max_chars=80).strip()
        email = st.text_input("Your email address", placeholder="you@example.com", max_chars=254).strip()
        st.caption("Your name and address stay in this session. Email is sent only when you click Send EcoSort Report.")
        submitted = st.form_submit_button("Let's go", type="primary")
    if submitted:
        if not name or not valid_email(email):
            st.warning("Enter your name and a valid email address.")
        else:
            st.session_state.name = name
            st.session_state.email = email
            st.session_state.onboarded = True
            st.session_state.sent_reports = set()
            start_conversation(st.session_state)
            st.rerun()
    st.stop()

with st.sidebar:
    st.title("♻️ EcoSort")
    st.caption("A little clarity. Less waste.")
    st.write("Welcome,", st.session_state.name)
    st.caption("Reports go to " + st.session_state.email)
    st.divider()
    st.subheader("How it works")
    st.markdown("**01 · Share**  \nUpload a photo or ask a waste question.")
    st.markdown("**02 · Understand**  \nReview items and disposal guidance.")
    st.markdown("**03 · Take action**  \nGenerate, download, or email your summary.")
    st.divider()
    if st.button("Start new conversation"):
        start_conversation(st.session_state)
        st.rerun()
    st.caption("Starting a new conversation clears photos, chat, and report. Your profile stays saved for this session.")
    st.caption("Photos and questions are sent to Gemini when you analyze, chat, or summarize. Local disposal rules vary.")

st.caption("EVERYDAY ACTIONS · A CLEANER PLANET")
st.title("Sort smarter. Waste less.")
st.write("Turn a waste photo or a question into practical disposal guidance.")
st.divider()
upload_panel, results_panel = st.columns([1, 1.8], gap="large")

with upload_panel, st.container(border=True):
    st.subheader("01 · Your photo")
    st.caption("JPG or PNG · Up to 10 MB · Under 20 million pixels")
    uploaded_file = st.file_uploader("Upload a waste image", type=["jpg", "jpeg", "png"],
                                    key=f"photo_{st.session_state.upload_version}")
    image = None
    if uploaded_file is not None:
        try:
            image = prepare_image(uploaded_file.getvalue())
            st.image(image, caption="Selected photo · click Analyze Waste to add it")
        except ValueError as error:
            st.warning(str(error))
    if image is not None and st.button("Analyze Waste", type="primary", width="stretch"):
        try:
            analyze_photo(uploaded_file.getvalue())
        except (EcoSortError, ValueError) as error:
            st.warning(str(error))
        except Exception:
            show_unexpected_error()
    st.caption("Each analyzed photo joins this conversation. Reanalyzing the same file replaces its item counts.")

with results_panel:
    data = combined_analysis(st.session_state)
    items = data["items"]
    counts = count_categories(items)
    score = calculate_recyclability_score(items, counts)
    st.subheader("02 · Your sorting guide")
    metric_columns = st.columns(3)
    metric_columns[0].metric("Items detected", len(items), border=True)
    metric_columns[1].metric("Recyclability score", f"{score:.2f}%", border=True)
    metric_columns[2].metric("Hazardous items", counts["Hazardous"], border=True)
    st.caption("Counts cover analyzed photos in this conversation, not items mentioned only in text. Different photos may show the same physical item.")
    items_tab, chat_tab, report_tab = st.tabs(["Detected items", "Ask EcoSort", "Your report"])
    with items_tab:
        st.subheader("Detected waste items")
        if not st.session_state.analyses:
            st.info("Upload and analyze a photo, or start with a question in Ask EcoSort.")
        elif not items:
            st.info("No clear waste items were detected. Try a closer, well-lit photo.")
        for index, item in enumerate(items, 1):
            with st.expander(f"{index}. {item['item_name']}", expanded=True):
                st.write("Material:", item["material"])
                st.write("Category:", item["waste_category"])
                st.write("Disposal:", item["disposal_method"])
        st.subheader("Waste category summary")
        st.dataframe([{"Category": category, "Items": count} for category, count in counts.items()], hide_index=True)
        st.caption("Recyclability = recyclable item count ÷ total detected item count × 100. It does not measure weight.")
    with chat_tab:
        st.subheader("Ask EcoSort")
        st.caption("Try: Which item is hazardous? Can this bottle be reused?")
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message.get("kind") == "image":
                    st.image(message["content"], caption="Waste photo shared in this conversation")
                else:
                    st.write(message["content"])
        user_input = st.chat_input("Ask about waste or attach a photo", max_chars=2000,
                                   accept_file=True, file_type=["jpg", "jpeg", "png"], max_upload_size=10)
        if user_input:
            text = user_input.text.strip()
            photo = user_input.files[0] if user_input.files else None
            changed = False
            try:
                if photo is not None:
                    analyze_photo(photo.getvalue())
                    changed = True
                if text:
                    with st.spinner("Thinking…"):
                        answer = answer_question(get_gemini_client(), combined_analysis(st.session_state),
                                                 st.session_state.messages, text)
                    st.session_state.messages.extend([
                        {"role": "user", "kind": "text", "content": text},
                        {"role": "assistant", "kind": "text", "content": answer},
                    ])
                    st.session_state.report = None
                    changed = True
            except (EcoSortError, ValueError) as error:
                st.session_state.chat_error = str(error)
            except Exception:
                st.session_state.chat_error = "Something went wrong. Please try again or check the app configuration."
            if changed:
                st.rerun()
        if st.session_state.get("chat_error"):
            st.warning(st.session_state.pop("chat_error"))
    with report_tab:
        st.subheader("Your EcoSort report")
        st.caption("A Gemini summary of the full conversation, with Python-calculated totals and the full text transcript. Photos are omitted from the email.")
        ready = has_conversation(st.session_state)
        if st.button("Generate report", type="primary", disabled=not ready):
            try:
                with st.spinner("Summarizing your conversation…"):
                    st.session_state.report = build_report()
            except EcoSortError as error:
                st.warning(str(error))
            except Exception:
                show_unexpected_error()
        report = st.session_state.report
        if report:
            st.text_area("Report preview", value=report, height=300, disabled=True)
            st.download_button("Download report", report, "ecosort-report.txt", "text/plain")
        st.divider()
        st.markdown("#### Email your report")
        st.caption("Recipient: " + st.session_state.email + ". If needed, this button generates the report first.")
        if st.button("Send EcoSort Report", type="primary", disabled=not ready):
            try:
                with st.spinner("Preparing your report…"):
                    if not st.session_state.report:
                        st.session_state.report = build_report()
                report = st.session_state.report
                delivery_id = hashlib.sha256((st.session_state.email + "\n" + report).encode()).hexdigest()
                if delivery_id in st.session_state.sent_reports:
                    st.info("This report has already been submitted to the mail server for this address.")
                else:
                    with st.spinner("Sending your report…"):
                        send_report(st.session_state.email, report)
                    st.session_state.sent_reports.add(delivery_id)
                    st.success("Report accepted by the mail server. Check your inbox and spam folder.")
            except (EcoSortError, EmailError) as error:
                st.warning(str(error))
            except Exception:
                show_unexpected_error()
        if not ready:
            st.caption("Ask a question or analyze a photo to enable reports.")

st.divider()
st.caption("EcoSort AI · Small choices add up. AI guidance may be uncertain; check local disposal rules.")
