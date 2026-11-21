import streamlit as st
import pandas as pd

# ==================================================
# 1. Page Configuration
# ==================================================

st.set_page_config(
    page_title="PaperSift",
    page_icon="📚",
    layout="wide"
)

# ==================================================
# 2. Mock Research Papers (T2)
# ==================================================

MOCK_PAPERS = [
    {
        "Title": "AI-Based Intrusion Detection Systems",
        "Year": 2025,
        "Score": 95,
        "Reasoning": (
            "Strong relevance to cybersecurity, "
            "machine learning and intrusion detection."
        ),
        "PDF Link": "https://arxiv.org/pdf/2501.00001"
    },
    {
        "Title": "Machine Learning in Cybersecurity",
        "Year": 2024,
        "Score": 89,
        "Reasoning": (
            "Discusses machine learning methods "
            "for detecting and preventing cyber attacks."
        ),
        "PDF Link": "https://arxiv.org/pdf/2401.00001"
    },
    {
        "Title": "Deep Learning for Network Security",
        "Year": 2023,
        "Score": 82,
        "Reasoning": (
            "Explores deep learning techniques "
            "for network threat detection."
        ),
        "PDF Link": "https://arxiv.org/pdf/2301.00001"
    },
    {
        "Title": "Artificial Intelligence in Healthcare",
        "Year": 2024,
        "Score": 65,
        "Reasoning": (
            "Uses AI techniques, but has limited "
            "connection to cybersecurity."
        ),
        "PDF Link": "https://arxiv.org/pdf/2402.00001"
    },
    {
        "Title": "A Survey of Generative AI Models",
        "Year": 2025,
        "Score": 76,
        "Reasoning": (
            "Provides an overview of generative AI "
            "with some relevant applications."
        ),
        "PDF Link": "https://arxiv.org/pdf/2502.00001"
    },
    {
        "Title": "Large Language Models for Security",
        "Year": 2026,
        "Score": 92,
        "Reasoning": (
            "Highly relevant research on using LLMs "
            "for security analysis."
        ),
        "PDF Link": "https://arxiv.org/pdf/2601.00001"
    }
]


# ==================================================
# 3. Application Header
# ==================================================

st.title("📚 PaperSift")
st.caption("Find the papers that matter to your research, automatically.")

st.divider()


# ==================================================
# 4. Navigation Tabs
# ==================================================

settings_tab, results_tab = st.tabs([
    "⚙️ Settings",
    "📊 Research Results"
])


# ==================================================
# 5. T1 - Settings Page
# ==================================================

with settings_tab:

    st.header("Research Agent Configuration")

    st.write(
        "Configure your research project and AI provider."
    )

    st.divider()

    # Project Information
    st.subheader("1. Project Information")

    project_title = st.text_input(
        "Project Title",
        placeholder="e.g. AI in Cybersecurity"
    )

    # AI Provider
    st.subheader("2. AI Provider")

    provider = st.selectbox(
        "Provider",
        [
            "Ollama",
            "Gemini",
            "OpenAI-compatible"
        ]
    )

    model_name = st.text_input(
        "Model Name",
        placeholder="e.g. llama3, gemini-2.0-flash"
    )

    api_key = st.text_input(
        "API Key",
        type="password",
        placeholder="Enter your API key"
    )

    if provider == "Ollama":
        st.caption(
            "Ollama runs locally and does not require an API key."
        )

    st.divider()

    # Search Parameters
    st.subheader("3. Search Parameters")

    relevance_threshold = st.slider(
        "Relevance Threshold",
        min_value=0,
        max_value=100,
        value=80,
        help="Minimum relevance score required for a paper."
    )

    days_to_search = st.number_input(
        "Days to Search Back",
        min_value=1,
        max_value=3650,
        value=365,
        step=1
    )

    st.divider()

    # Run Button
    if st.button(
        "🚀 Run Research Agent",
        width="stretch"
    ):

        if not project_title.strip():
            st.error("Please enter a project title.")

        elif not model_name.strip():
            st.error("Please enter a model name.")

        elif provider != "Ollama" and not api_key.strip():
            st.error("Please enter your API key.")

        else:

            settings = {
                "project_title": project_title.strip(),
                "provider": provider,
                "model_name": model_name.strip(),
                "relevance_threshold": relevance_threshold,
                "days_to_search": days_to_search
            }

            st.session_state["settings"] = settings

            st.success("Settings received successfully!")

            st.subheader("Configuration Summary")

            st.json(settings)

            # Never display or print the API key.
            st.caption(
                "API key received for this session and not displayed."
            )


# ==================================================
# 6. T2 - Results Page
# ==================================================

with results_tab:

    st.header("Research Results")

    st.write(
        "Explore and evaluate research papers related to your project."
    )

    st.info(
        "Demo mode: These results are static mock data, "
        "not real search results from arXiv."
    )

    # Convert mock data into a Pandas DataFrame
    df = pd.DataFrame(MOCK_PAPERS)

    # ----------------------------------------------
    # Results Statistics
    # ----------------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Total Papers",
            len(df)
        )

    with col2:
        st.metric(
            "Average Score",
            f"{df['Score'].mean():.1f}/100"
        )

    with col3:
        st.metric(
            "Highest Score",
            f"{df['Score'].max()}/100"
        )

    st.divider()

    # ----------------------------------------------
    # Filtering and Sorting
    # ----------------------------------------------

    st.subheader("Filter and Sort Papers")

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        min_score = st.slider(
            "Minimum Relevance Score",
            min_value=0,
            max_value=100,
            value=0,
            key="results_min_score"
        )

    with col2:
        sort_by = st.selectbox(
            "Sort By",
            ["Score", "Year", "Title"],
            index=0
        )

    with col3:
        descending = st.checkbox(
            "Descending",
            value=True
        )

    # ----------------------------------------------
    # Apply Filtering
    # ----------------------------------------------

    filtered_df = df[
        df["Score"] >= min_score
    ].copy()

    # ----------------------------------------------
    # Apply Sorting
    # ----------------------------------------------

    filtered_df = filtered_df.sort_values(
        by=sort_by,
        ascending=not descending
    )

    st.caption(
        f"Showing {len(filtered_df)} of {len(df)} papers."
    )

    # ----------------------------------------------
    # Display Results Table
    # ----------------------------------------------

    st.subheader("Research Papers")

    if not filtered_df.empty:

        st.dataframe(
            filtered_df,
            column_config={
                "Title": st.column_config.TextColumn(
                    "Paper Title",
                    width="large"
                ),
                "Year": st.column_config.NumberColumn(
                    "Year",
                    format="%d"
                ),
                "Score": st.column_config.ProgressColumn(
                    "Relevance Score",
                    min_value=0,
                    max_value=100,
                    format="%d/100"
                ),
                "Reasoning": st.column_config.TextColumn(
                    "AI Reasoning",
                    width="large"
                ),
                "PDF Link": st.column_config.LinkColumn(
                    "PDF",
                    display_text="Open PDF ↗"
                )
            },
            hide_index=True,
            width="stretch"
        )

    else:

        st.warning(
            "No papers match the selected minimum score."
        )

    st.divider()

    st.caption(
        "PaperSift | Research Assistant | T2 Demo"
    )