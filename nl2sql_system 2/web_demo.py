"""
Web-based interactive demo using Streamlit
Run with: streamlit run web_demo.py
"""
import streamlit as st
from system import CorrectionSystem
from engine.execution import connect, execute
import pandas as pd

# Page config
st.set_page_config(
    page_title="NL2SQL HITL Correction System",
    page_icon="🤖",
    layout="wide"
)

# Initialize system
@st.cache_resource
def init_system():
    return CorrectionSystem("demo.sqlite"), connect("demo.sqlite")

sys, gold = init_system()

# Title
st.title("🤖 NL2SQL Human-in-the-Loop Correction System")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("📚 Demo Cases")
    cases = {
        "Case 1: Column Ambiguity": {
            "question": "List the names of schools in Alameda county.",
            "predicted": 'SELECT "School Name" FROM schools WHERE County=\'Alameda\'',
            "description": "Ambiguous column name: 'School Name' vs 'School'"
        },
        "Case 2: Case Sensitivity": {
            "question": "Schools in Alameda county.",
            "predicted": "SELECT School FROM schools WHERE County='alameda'",
            "description": "Wrong case: 'alameda' should be 'Alameda'"
        }
    }

    selected_case = st.selectbox("Select a case:", list(cases.keys()))
    case = cases[selected_case]

    st.info(case["description"])

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Input")
    st.markdown(f"**Question:**")
    st.info(case["question"])

    st.markdown(f"**Predicted SQL:**")
    st.code(case["predicted"], language="sql")

with col2:
    st.subheader("⚙️ System Status")
    status_placeholder = st.empty()

# Run button
if st.button("🚀 Run Correction System", type="primary", use_container_width=True):

    # Store user choices in session state
    if 'user_choice' not in st.session_state:
        st.session_state.user_choice = None
    if 'waiting_for_choice' not in st.session_state:
        st.session_state.waiting_for_choice = False

    with st.spinner("Checking SQL correctness..."):

        # Custom user function for web interface
        def web_user(q):
            st.session_state.waiting_for_choice = True
            st.session_state.question_data = q

            # Display options
            st.markdown("### 🤔 System needs your help!")
            st.warning("Multiple valid interpretations found. Please choose:")

            option_cols = st.columns(len(q["options"]))

            for i, opt in enumerate(q["options"]):
                with option_cols[i]:
                    letter = chr(65 + i)
                    st.markdown(f"**Option {letter}** ({opt['n_rows']} rows)")

                    # Convert to DataFrame for better display
                    df = pd.DataFrame(opt["rows"], columns=opt["columns"])
                    st.dataframe(df, use_container_width=True)

                    if st.button(f"Select {letter}", key=f"btn_{i}"):
                        st.session_state.user_choice = i
                        st.session_state.waiting_for_choice = False
                        st.rerun()

            # Wait for user choice
            while st.session_state.waiting_for_choice:
                st.stop()

            return st.session_state.user_choice

        # Logger
        logs = []
        def log(msg):
            logs.append(msg)
            status_placeholder.text("\n".join(logs))

        try:
            # Run correction
            final_sql, constraints, _ = sys.run(
                case["question"],
                case["predicted"],
                user=web_user,
                log=log
            )

            # Display results
            st.markdown("---")
            st.success("✅ Correction Complete!")

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("🔧 Corrected SQL")
                st.code(final_sql, language="sql")

                if constraints:
                    st.info(f"📝 Decisions: {', '.join(c.description for c in constraints)}")

            with col2:
                st.subheader("📊 Final Result")
                cols, rows = execute(gold, final_sql)

                if cols != "ERROR":
                    df = pd.DataFrame(rows, columns=cols)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.error("Query execution error")

        except Exception as e:
            st.error(f"Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
### 🎯 System Features
- **Ambiguity Detection**: Identifies when SQL has multiple valid interpretations
- **Auto-Fix**: Automatically corrects simple errors (case sensitivity, etc.)
- **Human-in-the-Loop**: Only asks users when truly ambiguous
- **Result-Based**: Shows actual data tables, not SQL code
- **Learning**: Records user preferences for future queries
""")
