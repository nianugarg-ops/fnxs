import re
import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Metric, RunReportRequest, Filter, FilterExpression
)

st.set_page_config(page_title="GA4 Local Reporter", layout="wide")
st.title("📊 GA4 Local Reporter")

# --- Sidebar inputs ---
with st.sidebar:
    st.header("Configuration")

    # File uploader for service account JSON
    uploaded_key_file = st.file_uploader("Upload Service Account JSON", type="json")

    property_id = st.text_input("GA4 Property ID", "322700238")
    start_date = st.text_input("Start Date", "7daysAgo")
    end_date = st.text_input("End Date", "today")
    regex_filter = st.text_input("Filter (regex)", r"^/at/article/.*\d+$")
    max_results = st.number_input("Max Results", min_value=1, value=20)

run_report = st.sidebar.button("Run Report")

# --- Run GA4 Report ---
if run_report:
    try:
        if not uploaded_key_file:
            st.error("⚠️ Please upload a Service Account JSON file.")
        elif not property_id:
            st.error("⚠️ Please provide a Property ID.")
        else:
            # Load credentials from uploaded JSON
            creds = service_account.Credentials.from_service_account_info(
                uploaded_key_file.getvalue(),
                scopes=["https://www.googleapis.com/auth/analytics.readonly"]
            )

            client = BetaAnalyticsDataClient(credentials=creds)

            # Optional regex filter
            filter_expression = None
            if regex_filter:
                filter_expression = FilterExpression(
                    filter=Filter(
                        field_name="pagePath",
                        string_filter=Filter.StringFilter(
                            match_type=Filter.StringFilter.MatchType.FULL_REGEXP,
                            value=regex_filter,
                            case_sensitive=False
                        )
                    )
                )

            request = RunReportRequest(
                property=f"properties/{property_id}",
                dimensions=[Dimension(name="pagePath")],
                metrics=[Metric(name="eventCount")],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                dimension_filter=filter_expression,
                limit=max_results
            )

            response = client.run_report(request)

            # Process rows into DataFrame
            data = []
            for row in response.rows:
                path = row.dimension_values[0].value
                count = int(row.metric_values[0].value)
                match = re.search(r'(\d+)$', path)
                page_id = match.group(1) if match else ""
                data.append((path, page_id, count))

            if data:
                df = pd.DataFrame(data, columns=["Page Path", "Page ID", "Event Count"])

                st.success(f"✅ Report loaded successfully ({len(df)} rows)")
                st.dataframe(df, use_container_width=True)

                # CSV download
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download CSV",
                    csv,
                    "ga4_report.csv",
                    "text/csv",
                    key="download-csv"
                )
            else:
                st.warning("No data returned for this query.")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
