"""Streamlit interface for the PaperSift research pipeline.

Run with: streamlit run papersift/gui/app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from papersift.core import Scout, ScoutResult
from papersift.gui.ollama import OllamaDiscoveryError, list_ollama_models
from papersift.providers import ProviderError, available_providers, create_provider
from papersift.ranking import AssessmentError
from papersift.sources import SourceError
from papersift.ranking.fulltext import FulltextError


PROVIDER_LABELS = {
    "ollama": "Ollama (local)",
    "gemini": "Google Gemini",
    "groq": "Groq",
    "openrouter": "OpenRouter",
    "together": "Together AI",
    "cerebras": "Cerebras",
    "mistral": "Mistral",
    "openai": "OpenAI",
    "openai_compat": "Custom OpenAI-compatible endpoint",
}


def _provider_label(provider_name: str) -> str:
    return PROVIDER_LABELS.get(provider_name, provider_name.replace("_", " ").title())


@st.cache_data(ttl=30, show_spinner=False)
def _cached_ollama_models(host: str) -> list[str]:
    return list_ollama_models(host)


def _result_frame(results: list[ScoutResult]) -> pd.DataFrame:
    rows = []
    for result in results:
        paper = result.paper
        assessment = result.abstract_assessment
        rows.append(
            {
                "Title": paper.title,
                "Year": paper.year,
                "Score": result.score,
                "Recommendation": assessment.recommendation,
                "Reasoning": assessment.rubric.reasoning,
                "Authors": ", ".join(paper.authors),
                "arXiv": paper.url,
                "PDF": paper.pdf_url,
                "_result": result,
            }
        )
    return pd.DataFrame(rows)


def _show_result_details(result: ScoutResult) -> None:
    paper = result.paper
    assessment = result.abstract_assessment
    rubric = assessment.rubric

    st.markdown(f"#### {paper.title}")
    st.caption(f"{paper.year} · {', '.join(paper.authors) or 'Authors unavailable'} · arXiv:{paper.arxiv_id}")
    st.write(paper.abstract)

    score_cols = st.columns(4)
    score_cols[0].metric("Final score", f"{result.score}/100")
    score_cols[1].metric("Topic match", f"{rubric.topic_match}/3")
    score_cols[2].metric("Method match", f"{rubric.method_match}/3")
    score_cols[3].metric("Novelty", f"{rubric.novelty}/3")

    st.markdown(f"**Recommendation:** {assessment.recommendation}")
    if rubric.reasoning:
        st.write(rubric.reasoning)

    left, right = st.columns(2)
    with left:
        st.markdown("**Key strengths**")
        if rubric.key_strengths:
            for item in rubric.key_strengths:
                st.markdown(f"- {item}")
        else:
            st.caption("No strengths were returned.")
    with right:
        st.markdown("**Potential limitations**")
        if rubric.potential_limitations:
            for item in rubric.potential_limitations:
                st.markdown(f"- {item}")
        else:
            st.caption("No limitations were returned.")

    if result.fulltext_assessment:
        fulltext = result.fulltext_assessment
        with st.expander("Full-text assessment"):
            st.write(f"Score: **{fulltext.score}/100** · {fulltext.recommendation}")
            st.write(fulltext.rubric.reasoning)

    links = st.columns(3)
    links[0].link_button("Open arXiv page", paper.url, use_container_width=True)
    if result.pdf_path and Path(result.pdf_path).exists():
        with open(result.pdf_path, "rb") as pdf_file:
            links[1].download_button(
                "Download saved PDF",
                data=pdf_file,
                file_name=Path(result.pdf_path).name,
                mime="application/pdf",
                use_container_width=True,
            )
    else:
        links[1].link_button("Open PDF", paper.pdf_url, use_container_width=True)
    if result.metadata_path and Path(result.metadata_path).exists():
        with open(result.metadata_path, "rb") as metadata_file:
            links[2].download_button(
                "Download metadata",
                data=metadata_file,
                file_name=Path(result.metadata_path).name,
                mime="application/json",
                use_container_width=True,
            )


def main() -> None:
    st.set_page_config(page_title="PaperSift", page_icon="📚", layout="wide")
    st.title("PaperSift")
    st.caption("Find the papers that matter to your research, automatically.")

    settings_tab, results_tab = st.tabs(["Settings", "Research results"])

    with settings_tab:
        st.header("Research agent configuration")
        st.write("Configure a research topic, an AI provider, and the search parameters.")

        project_title = st.text_input(
            "Research project",
            placeholder="e.g. Self-improving generative AI agents",
        )

        provider_names = available_providers()
        provider_name = st.selectbox(
            "Provider",
            options=provider_names,
            format_func=_provider_label,
        )
        api_key = ""
        base_url = ""
        if provider_name == "ollama":
            base_url = st.text_input(
                "Ollama host",
                value="http://localhost:11434",
                help="The address of the Ollama server.",
            )
            st.caption("Ollama runs locally and does not require an API key.")

            try:
                installed_models = _cached_ollama_models(base_url.strip() or "http://localhost:11434")
            except OllamaDiscoveryError as exc:
                installed_models = []
                st.warning(f"Could not discover Ollama models: {exc}")

            if installed_models:
                model_options = [*installed_models, "Enter a model name manually"]
                selected_model = st.selectbox("Installed Ollama model", model_options)
                if selected_model == "Enter a model name manually":
                    model_name = st.text_input("Model name", placeholder="e.g. llama3.1:8b")
                else:
                    model_name = selected_model
            else:
                st.info("No installed models were detected. Start Ollama and pull a model, or enter its name manually.")
                model_name = st.text_input("Model name", placeholder="e.g. llama3.1:8b")

            if st.button("Refresh installed models", key="refresh_ollama_models"):
                _cached_ollama_models.clear()
                st.rerun()
        elif provider_name == "openai_compat":
            model_name = st.text_input(
                "Model name",
                placeholder="e.g. provider-model-name",
            )
            base_url = st.text_input(
                "Base URL",
                placeholder="https://your-provider.example/v1",
            )
            api_key = st.text_input("API key", type="password")
        else:
            model_name = st.text_input(
                "Model name",
                placeholder="e.g. gemini-2.5-flash, gpt-4.1-mini",
            )
            api_key = st.text_input("API key", type="password")

        st.subheader("Search parameters")
        relevance_threshold = st.slider(
            "Minimum relevance score",
            min_value=0,
            max_value=100,
            value=80,
            help="Only papers meeting this final score are included in the results.",
        )
        days_to_search = st.number_input(
            "Search window (days)", min_value=1, max_value=3650, value=365, step=1
        )
        max_results = st.number_input(
            "Maximum candidate papers", min_value=1, max_value=500, value=100, step=10
        )
        fulltext = st.checkbox(
            "Enable full-text assessment",
            value=False,
            help="Downloads and evaluates the full text of the highest-scoring candidates. Requires PyMuPDF.",
        )
        output_dir = st.text_input("Output directory", value="papersift_output")

        submitted = st.button("Run research agent", type="primary", use_container_width=True)

        if submitted:
            if not project_title.strip():
                st.error("Enter a research project title.")
            elif not model_name.strip():
                st.error("Enter a model name.")
            elif provider_name != "ollama" and not api_key.strip():
                st.error("Enter the API key for the selected provider.")
            elif provider_name == "openai_compat" and not base_url.strip():
                st.error("Enter the base URL for the custom OpenAI-compatible provider.")
            elif provider_name == "ollama" and not base_url.strip():
                st.error("Enter the Ollama host URL.")
            else:
                try:
                    provider = create_provider(
                        provider_name,
                        model_name.strip(),
                        api_key=api_key.strip() or None,
                        base_url=base_url.strip() or None,
                    )
                    scout = Scout(
                        project_title=project_title.strip(),
                        provider=provider,
                        relevance_threshold=int(relevance_threshold),
                        since_days=int(days_to_search),
                        max_results=int(max_results),
                        output_dir=output_dir.strip() or "papersift_output",
                        fulltext=fulltext,
                    )
                    with st.spinner("PaperSift is generating search keywords, searching arXiv, and assessing papers..."):
                        results = scout.run()
                    st.session_state["papersift_results"] = results
                    st.session_state["papersift_project_title"] = project_title.strip()
                    st.session_state["papersift_run_config"] = {
                        "provider": provider_name,
                        "model": model_name.strip(),
                        "threshold": int(relevance_threshold),
                        "days": int(days_to_search),
                        "max_results": int(max_results),
                        "fulltext": fulltext,
                        "output_dir": output_dir.strip() or "papersift_output",
                    }
                    st.success(f"Research completed. {len(results)} relevant paper(s) found.")
                    st.info("API credentials are used to create the provider and are not included in the saved run configuration.")
                except (ProviderError, SourceError, AssessmentError, FulltextError, ValueError) as exc:
                    st.error(f"Research could not be completed: {exc}")
                except Exception as exc:  # noqa: BLE001 - keep unexpected runtime failures visible in the UI
                    st.exception(exc)

    with results_tab:
        st.header("Research results")
        results = st.session_state.get("papersift_results", [])
        project_title = st.session_state.get("papersift_project_title")

        if not results:
            st.info("No research results yet. Configure your project and run the research agent from the Settings tab.")
        else:
            st.caption(f"Project: {project_title}")
            df = _result_frame(results)

            metric_cols = st.columns(3)
            metric_cols[0].metric("Papers retained", len(results))
            metric_cols[1].metric("Average score", f"{df['Score'].mean():.1f}/100")
            metric_cols[2].metric("Highest score", f"{df['Score'].max()}/100")

            st.subheader("Filter and sort")
            filter_cols = st.columns([2, 2, 1])
            min_score = filter_cols[0].slider(
                "Minimum score", 0, 100, 0, key="results_min_score"
            )
            sort_by = filter_cols[1].selectbox(
                "Sort by", ["Score", "Year", "Title"], key="results_sort_by"
            )
            descending = filter_cols[2].checkbox(
                "Descending", value=True, key="results_descending"
            )

            filtered = df[df["Score"] >= min_score].sort_values(
                by=sort_by, ascending=not descending
            )
            st.caption(f"Showing {len(filtered)} of {len(df)} retained papers.")
            display_df = filtered.drop(columns=["_result"])
            st.dataframe(
                display_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Title": st.column_config.TextColumn("Paper title", width="large"),
                    "Score": st.column_config.ProgressColumn(
                        "Relevance score", min_value=0, max_value=100, format="%d/100"
                    ),
                    "arXiv": st.column_config.LinkColumn("arXiv", display_text="Open paper"),
                    "PDF": st.column_config.LinkColumn("PDF / saved path"),
                    "Reasoning": st.column_config.TextColumn("Assessment reasoning", width="large"),
                },
            )

            st.subheader("Paper assessments")
            for _, row in filtered.iterrows():
                result = row["_result"]
                with st.expander(f"{result.score}/100 · {result.paper.title}"):
                    _show_result_details(result)

    st.divider()
    st.caption("PaperSift · Research assistant")


if __name__ == "__main__":
    main()
