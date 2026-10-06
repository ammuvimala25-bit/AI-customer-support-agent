import os
import json
from datetime import datetime

import requests
import streamlit as st
from dotenv import load_dotenv


# =========================================================
# CONFIG
# =========================================================

load_dotenv()

APP_TITLE = "🤖 Vimala AI Support Agent"

MODEL = os.getenv(
    "MODEL",
    "Qwen/Qwen3.8-27B"
).strip()

HF_TOKEN = os.getenv(
    "HF_TOKEN",
    ""
).strip()

SERPAPI_KEY = os.getenv(
    "SERPAPI_KEY",
    ""
).strip()

MEMORY_FILE = "customer_memory.json"
TICKET_FILE = "tickets.json"
KNOWLEDGE_FOLDER = "knowledge_base"


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🤖",
    layout="wide"
)


# =========================================================
# UI STYLE
# =========================================================

st.markdown(
    """
    <style>

    .stApp {
        background:
            radial-gradient(
                circle at 10% 10%,
                #dcecff 0%,
                transparent 30%
            ),
            radial-gradient(
                circle at 90% 10%,
                #eadcff 0%,
                transparent 30%
            ),
            linear-gradient(
                135deg,
                #f8fbff,
                #f8f1ff,
                #fff7fb
            );
    }

    .hero {
        background: rgba(255,255,255,0.75);
        border: 1px solid rgba(255,255,255,0.9);
        border-radius: 25px;
        padding: 28px;
        text-align: center;
        box-shadow: 0 8px 30px rgba(80,70,120,0.10);
        margin-bottom: 20px;
    }

    .hero-title {
        font-size: 38px;
        font-weight: 800;
        color: #5b21b6;
    }

    .online {
        color: #159447;
        font-weight: 700;
    }

    .card {
        background: rgba(255,255,255,0.75);
        border: 1px solid rgba(255,255,255,0.9);
        border-radius: 20px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 7px 25px rgba(80,70,120,0.08);
    }

    .stButton > button {
        border-radius: 13px;
        border: 1px solid #ddd6fe;
        background: rgba(255,255,255,0.85);
        font-weight: 600;
    }

    input,
    textarea {
        border-radius: 12px !important;
    }

    section[data-testid="stSidebar"] {
        background: rgba(245,248,255,0.95);
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# FILE SETUP
# =========================================================

os.makedirs(
    KNOWLEDGE_FOLDER,
    exist_ok=True
)


def ensure_json_file(filename, default):

    if not os.path.exists(filename):

        try:

            with open(
                filename,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    default,
                    f,
                    indent=2,
                    ensure_ascii=False
                )

        except Exception:
            pass


ensure_json_file(
    MEMORY_FILE,
    {}
)

ensure_json_file(
    TICKET_FILE,
    []
)


# =========================================================
# SESSION STATE
# =========================================================

DEFAULT_CUSTOMER_ID = "customer001"

if "customer_id" not in st.session_state:
    st.session_state.customer_id = DEFAULT_CUSTOMER_ID

if not st.session_state.customer_id:
    st.session_state.customer_id = DEFAULT_CUSTOMER_ID


if "customer_name" not in st.session_state:
    st.session_state.customer_name = ""


if "messages" not in st.session_state:
    st.session_state.messages = []


if "last_questions" not in st.session_state:
    st.session_state.last_questions = []


if "search_mode" not in st.session_state:
    st.session_state.search_mode = "💬 AI Chat"


# =========================================================
# JSON FUNCTIONS
# =========================================================

def load_json(filename, default):

    try:

        if not os.path.exists(filename):
            return default

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        return data

    except Exception:

        return default


def save_json(filename, data):

    try:

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=2,
                ensure_ascii=False
            )

        return True

    except Exception:

        return False


# =========================================================
# CUSTOMER MEMORY CREATOR
# =========================================================

def create_customer_memory(customer_id):

    return {
        "customer_id": customer_id,
        "name": "",
        "created_at": datetime.now().isoformat(),
        "questions": [],
        "conversations": []
    }


# =========================================================
# GET / REPAIR CUSTOMER MEMORY
# =========================================================

def get_memory():

    data = load_json(
        MEMORY_FILE,
        {}
    )

    if not isinstance(data, dict):
        data = {}

    customer_id = (
        st.session_state.get(
            "customer_id",
            DEFAULT_CUSTOMER_ID
        )
        or DEFAULT_CUSTOMER_ID
    )

    # Create customer
    if customer_id not in data:

        data[customer_id] = (
            create_customer_memory(
                customer_id
            )
        )

    customer = data.get(
        customer_id
    )

    # Repair invalid customer
    if not isinstance(
        customer,
        dict
    ):

        customer = (
            create_customer_memory(
                customer_id
            )
        )

    # -----------------------------------------------------
    # Repair missing keys
    # -----------------------------------------------------

    customer.setdefault(
        "customer_id",
        customer_id
    )

    customer.setdefault(
        "name",
        ""
    )

    customer.setdefault(
        "created_at",
        datetime.now().isoformat()
    )

    customer.setdefault(
        "questions",
        []
    )

    customer.setdefault(
        "conversations",
        []
    )

    # -----------------------------------------------------
    # Repair wrong data types
    # -----------------------------------------------------

    if not isinstance(
        customer["questions"],
        list
    ):

        customer["questions"] = []


    if not isinstance(
        customer["conversations"],
        list
    ):

        customer["conversations"] = []


    # Always keep correct customer ID
    customer["customer_id"] = customer_id

    data[customer_id] = customer

    save_json(
        MEMORY_FILE,
        data
    )

    return customer


# =========================================================
# SAVE LONG-TERM MEMORY
# =========================================================

def save_memory(
    question,
    answer
):

    data = load_json(
        MEMORY_FILE,
        {}
    )

    if not isinstance(data, dict):
        data = {}

    customer_id = (
        st.session_state.get(
            "customer_id",
            DEFAULT_CUSTOMER_ID
        )
        or DEFAULT_CUSTOMER_ID
    )

    # Create customer
    if customer_id not in data:

        data[customer_id] = (
            create_customer_memory(
                customer_id
            )
        )

    customer = data.get(
        customer_id
    )

    # Repair customer
    if not isinstance(
        customer,
        dict
    ):

        customer = (
            create_customer_memory(
                customer_id
            )
        )

    customer.setdefault(
        "customer_id",
        customer_id
    )

    customer.setdefault(
        "name",
        ""
    )

    customer.setdefault(
        "created_at",
        datetime.now().isoformat()
    )

    customer.setdefault(
        "questions",
        []
    )

    customer.setdefault(
        "conversations",
        []
    )

    if not isinstance(
        customer["questions"],
        list
    ):

        customer["questions"] = []


    if not isinstance(
        customer["conversations"],
        list
    ):

        customer["conversations"] = []


    # -----------------------------------------------------
    # Save customer details
    # -----------------------------------------------------

    customer["customer_id"] = customer_id

    customer["name"] = (
        st.session_state.get(
            "customer_name",
            ""
        )
    )

    customer["questions"].append(
        str(question)
    )

    customer["conversations"].append(
        {
            "time":
                datetime.now().isoformat(),

            "question":
                str(question),

            "answer":
                str(answer)
        }
    )

    # Keep last 100
    customer["questions"] = (
        customer["questions"][-100:]
    )

    customer["conversations"] = (
        customer["conversations"][-100:]
    )

    data[customer_id] = customer

    save_json(
        MEMORY_FILE,
        data
    )


# =========================================================
# MEMORY TEXT FOR AI
# =========================================================

def memory_text():

    customer = get_memory()

    text = ""

    name = customer.get(
        "name",
        ""
    )

    if name:

        text += (
            f"Customer name: "
            f"{name}\n"
        )

    questions = customer.get(
        "questions",
        []
    )

    conversations = customer.get(
        "conversations",
        []
    )

    if not isinstance(
        questions,
        list
    ):

        questions = []


    if not isinstance(
        conversations,
        list
    ):

        conversations = []


    if questions:

        text += "\nPrevious questions:\n"

        for q in questions[-10:]:

            text += f"- {q}\n"


    if conversations:

        text += "\nRecent conversations:\n"

        for item in conversations[-5:]:

            if not isinstance(
                item,
                dict
            ):
                continue

            old_question = item.get(
                "question",
                ""
            )

            old_answer = item.get(
                "answer",
                ""
            )

            text += (
                f"Customer: "
                f"{old_question}\n"
                f"AI: "
                f"{old_answer}\n"
            )

    return text


# =========================================================
# KNOWLEDGE BASE
# =========================================================

def load_knowledge():

    documents = []

    if not os.path.exists(
        KNOWLEDGE_FOLDER
    ):

        return documents


    try:

        files = os.listdir(
            KNOWLEDGE_FOLDER
        )

    except Exception:

        return documents


    for filename in files:

        if not filename.lower().endswith(
            (
                ".txt",
                ".md",
                ".csv"
            )
        ):

            continue


        path = os.path.join(
            KNOWLEDGE_FOLDER,
            filename
        )

        try:

            with open(
                path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as f:

                content = f.read()


            if content.strip():

                documents.append(
                    {
                        "file": filename,
                        "text": content
                    }
                )

        except Exception:

            continue


    return documents


# =========================================================
# KNOWLEDGE SEARCH
# =========================================================

def knowledge_search(query):

    documents = load_knowledge()

    if not query:
        return []

    query_words = set(
        word.lower()
        for word in query.split()
        if len(word.strip()) > 1
    )

    results = []

    for document in documents:

        text = document.get(
            "text",
            ""
        )

        text_lower = text.lower()

        score = 0

        for word in query_words:

            if word in text_lower:
                score += 1


        if score > 0:

            results.append(
                {
                    "file":
                        document.get(
                            "file",
                            "Unknown"
                        ),

                    "text":
                        text,

                    "score":
                        score
                }
            )


    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return results[:5]


# =========================================================
# ONLINE SEARCH
# =========================================================

def online_search(query):

    if not SERPAPI_KEY:

        return {
            "error":
                "SERPAPI_KEY is missing in .env"
        }


    if not query:

        return {
            "error":
                "Please enter a search query."
        }


    try:

        response = requests.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google",
                "q": query,
                "api_key": SERPAPI_KEY,
                "num": 8,
                "hl": "en",
                "gl": "in"
            },
            timeout=20
        )


        if response.status_code != 200:

            return {
                "error":
                    f"Search error: "
                    f"{response.status_code}"
            }


        data = response.json()

        results = []


        for item in data.get(
            "organic_results",
            []
        ):

            results.append(
                {
                    "title":
                        item.get(
                            "title",
                            ""
                        ),

                    "link":
                        item.get(
                            "link",
                            ""
                        ),

                    "snippet":
                        item.get(
                            "snippet",
                            ""
                        )
                }
            )


        return {
            "results":
                results[:8]
        }


    except Exception as e:

        return {
            "error":
                f"Search connection error: {e}"
        }


# =========================================================
# SPECIAL SEARCHES
# =========================================================

def product_search(query):

    return online_search(
        f"{query} product price features India"
    )


def books_search(query):

    return online_search(
        f"{query} TNPSC books Tamil Nadu"
    )


def notification_search(query):

    return online_search(
        f"{query} TNPSC notification Tamil Nadu"
    )


def results_search(query):

    return online_search(
        f"{query} TNPSC results Tamil Nadu"
    )


# =========================================================
# DISPLAY SEARCH RESULTS
# =========================================================

def show_results(data):

    if not isinstance(
        data,
        dict
    ):

        st.error(
            "Invalid search response."
        )

        return


    if data.get("error"):

        st.error(
            data["error"]
        )

        return


    results = data.get(
        "results",
        []
    )


    if not results:

        st.info(
            "No results found."
        )

        return


    for number, result in enumerate(
        results,
        1
    ):

        title = result.get(
            "title",
            "Untitled"
        )

        snippet = result.get(
            "snippet",
            ""
        )

        link = result.get(
            "link",
            ""
        )


        st.markdown(
            f"""
            <div class="card">

            <h4>
            {number}. {title}
            </h4>

            <p>
            {snippet}
            </p>

            </div>
            """,
            unsafe_allow_html=True
        )


        if link:

            st.markdown(
                f"[🌐 Open result]({link})"
            )


# =========================================================
# AI MODEL
# =========================================================

def ask_ai(
    question,
    knowledge=""
):

    if not HF_TOKEN:

        return (
            "⚠️ HF_TOKEN is missing.\n\n"
            "Please add your Hugging Face token "
            "to the `.env` file."
        )


    prompt = f"""
You are Vimala AI Support Agent.

Model:
{MODEL}

Rules:

- Answer clearly and simply.
- Use supplied knowledge when available.
- Use customer memory when useful.
- Do not invent company information.
- Do not make up prices, policies, orders or products.
- If information is unavailable, say so.
- Keep the answer concise.
- If the customer asks for a human agent, say that human support can be requested.

Customer memory:
{memory_text()}

Knowledge Base:
{knowledge}

Customer question:
{question}
"""


    payload = {
        "model": MODEL,

        "messages": [
            {
                "role":
                    "user",

                "content":
                    prompt
            }
        ],

        "temperature":
            0.2,

        "max_tokens":
            400
    }


    headers = {
        "Authorization":
            f"Bearer {HF_TOKEN}",

        "Content-Type":
            "application/json"
    }


    endpoints = [

        "https://router.huggingface.co/v1/chat/completions",

        "https://api-inference.huggingface.co/v1/chat/completions"
    ]


    last_error = ""


    for endpoint in endpoints:

        try:

            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=90
            )


            if response.status_code == 200:

                data = response.json()

                choices = data.get(
                    "choices",
                    []
                )


                if choices:

                    message = choices[0].get(
                        "message",
                        {}
                    )


                    answer = message.get(
                        "content",
                        ""
                    )


                    if answer:

                        return answer.strip()


            last_error = (
                f"HTTP "
                f"{response.status_code}: "
                f"{response.text[:500]}"
            )


        except Exception as e:

            last_error = str(e)


    return (
        "⚠️ AI connection error.\n\n"
        f"{last_error}"
    )


# =========================================================
# CREATE TICKET
# =========================================================

def create_ticket(issue):

    tickets = load_json(
        TICKET_FILE,
        []
    )


    if not isinstance(
        tickets,
        list
    ):

        tickets = []


    ticket_number = (
        len(tickets) + 1
    )


    ticket_id = (
        "TKT-"
        + datetime.now().strftime(
            "%Y%m%d"
        )
        + "-"
        + str(
            ticket_number
        ).zfill(4)
    )


    ticket = {

        "ticket_id":
            ticket_id,

        "customer_id":
            st.session_state.get(
                "customer_id",
                DEFAULT_CUSTOMER_ID
            ),

        "customer_name":
            st.session_state.get(
                "customer_name",
                ""
            ),

        "issue":
            issue,

        "status":
            "Open",

        "created_at":
            datetime.now().isoformat()
    }


    tickets.append(
        ticket
    )


    save_json(
        TICKET_FILE,
        tickets
    )


    return ticket


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        """
        <div class="card">

        <h2>⚙️ Agent Controls</h2>

        </div>
        """,
        unsafe_allow_html=True
    )


    customer_id_input = st.text_input(
        "👤 Customer ID",
        value=st.session_state.get(
            "customer_id",
            DEFAULT_CUSTOMER_ID
        )
    )


    if customer_id_input.strip():

        st.session_state.customer_id = (
            customer_id_input.strip()
        )

    else:

        st.session_state.customer_id = (
            DEFAULT_CUSTOMER_ID
        )


    st.session_state.customer_name = (
        st.text_input(
            "Customer Name",
            value=st.session_state.get(
                "customer_name",
                ""
            )
        )
    )


    st.divider()


    st.markdown(
        "### 🔎 Search Tools"
    )


    search_mode = st.radio(
        "Choose search mode",
        [
            "💬 AI Chat",
            "📚 Knowledge Base",
            "🌐 Web Search",
            "🛍️ Product Search",
            "📖 TNPSC Books",
            "🔔 TNPSC Notifications",
            "🏆 TNPSC Results"
        ],
        index=0
    )


    st.session_state.search_mode = (
        search_mode
    )


    st.divider()


    documents = load_knowledge()


    st.info(
        f"📚 Knowledge Files: "
        f"{len(documents)}"
    )


    st.caption(
        f"🤖 Model: {MODEL}"
    )


    st.caption(
        "🧠 Long-Term Memory: ON"
    )


    st.caption(
        f"👤 ID: "
        f"{st.session_state.customer_id}"
    )


    st.divider()


    if st.button(
        "🗑️ Clear Chat",
        use_container_width=True
    ):

        st.session_state.messages = []

        st.session_state.last_questions = []

        st.rerun()


# =========================================================
# HEADER
# =========================================================

st.markdown(
    """
    <div class="hero">

    <div class="hero-title">
    🤖 Vimala AI Support Agent
    </div>

    <div class="online">
    🟢 AI Customer Support Agent is Online
    </div>

    <p>
    RAG • Online Product Search • TNPSC Books •
    Tickets • Human Escalation • Long-Term Memory •
    Notifications • Results
    </p>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# CURRENT SEARCH MODE
# =========================================================

search_mode = st.session_state.get(
    "search_mode",
    "💬 AI Chat"
)


# =========================================================
# KNOWLEDGE BASE SEARCH
# =========================================================

if search_mode == "📚 Knowledge Base":

    st.markdown(
        "## 📚 Knowledge Base Search"
    )


    query = st.text_input(
        "Search knowledge base",
        placeholder="Example: refund policy"
    )


    if query:

        results = knowledge_search(
            query
        )


        if not results:

            st.warning(
                "No matching knowledge found."
            )


        for result in results:

            st.markdown(
                f"""
                <div class="card">

                <h4>
                📄 {result.get('file', 'Unknown')}
                </h4>

                <p>
                {result.get('text', '')[:3000]}
                </p>

                </div>
                """,
                unsafe_allow_html=True
            )


# =========================================================
# WEB SEARCH
# =========================================================

elif search_mode == "🌐 Web Search":

    st.markdown(
        "## 🌐 Web Search"
    )


    query = st.text_input(
        "Search online"
    )


    if st.button(
        "🔎 Search"
    ):

        if query.strip():

            with st.spinner(
                "Searching..."
            ):

                data = online_search(
                    query
                )


            show_results(
                data
            )


# =========================================================
# PRODUCT SEARCH
# =========================================================

elif search_mode == "🛍️ Product Search":

    st.markdown(
        "## 🛍️ Online Product Search"
    )


    query = st.text_input(
        "Product name",
        placeholder="Example: Hair Oil"
    )


    if st.button(
        "🔎 Search Product"
    ):

        if query.strip():

            with st.spinner(
                "Searching product..."
            ):

                data = product_search(
                    query
                )


            show_results(
                data
            )


# =========================================================
# TNPSC BOOKS
# =========================================================

elif search_mode == "📖 TNPSC Books":

    st.markdown(
        "## 📖 TNPSC Books Search"
    )


    query = st.text_input(
        "Book search",
        placeholder="Example: TNPSC Group 4 books"
    )


    if st.button(
        "🔎 Search Books"
    ):

        if query.strip():

            with st.spinner(
                "Searching books..."
            ):

                data = books_search(
                    query
                )


            show_results(
                data
            )


# =========================================================
# TNPSC NOTIFICATIONS
# =========================================================

elif search_mode == "🔔 TNPSC Notifications":

    st.markdown(
        "## 🔔 TNPSC Notifications"
    )


    query = st.text_input(
        "Notification search",
        placeholder="Example: TNPSC Group 4 notification"
    )


    if st.button(
        "🔎 Search Notifications"
    ):

        if query.strip():

            with st.spinner(
                "Searching notifications..."
            ):

                data = notification_search(
                    query
                )


            show_results(
                data
            )


# =========================================================
# TNPSC RESULTS
# =========================================================

elif search_mode == "🏆 TNPSC Results":

    st.markdown(
        "## 🏆 TNPSC Results"
    )


    query = st.text_input(
        "Result search",
        placeholder="Example: TNPSC Group 4 results"
    )


    if st.button(
        "🔎 Search Results"
    ):

        if query.strip():

            with st.spinner(
                "Searching results..."
            ):

                data = results_search(
                    query
                )


            show_results(
                data
            )


# =========================================================
# AI CHAT
# =========================================================

else:

    st.markdown(
        """
        <div class="card">

        <h2>👋 Welcome!</h2>

        <p>
        I am Vimala AI Support Agent.
        Ask me about refunds, shipping, warranty,
        products, orders, books, or support issues.
        </p>

        </div>
        """,
        unsafe_allow_html=True
    )


    # -----------------------------------------------------
    # DISPLAY OLD CHAT
    # -----------------------------------------------------

    messages = st.session_state.get(
        "messages",
        []
    )


    if not isinstance(
        messages,
        list
    ):

        messages = []

        st.session_state.messages = []


    for message in messages:

        if not isinstance(
            message,
            dict
        ):
            continue


        role = message.get(
            "role",
            "assistant"
        )

        content = message.get(
            "content",
            ""
        )


        with st.chat_message(
            role
        ):

            st.markdown(
                content
            )


    # -----------------------------------------------------
    # CHAT INPUT
    # -----------------------------------------------------

    question = st.chat_input(
        "💬 Type your question..."
    )


    if question:

        question = question.strip()


        if not question:
            st.stop()


        # -------------------------------------------------
        # USER MESSAGE
        # -------------------------------------------------

        st.session_state.messages.append(
            {
                "role":
                    "user",

                "content":
                    question
            }
        )


        # -------------------------------------------------
        # LAST QUESTIONS
        # -------------------------------------------------

        if "last_questions" not in st.session_state:

            st.session_state.last_questions = []


        if not isinstance(
            st.session_state.last_questions,
            list
        ):

            st.session_state.last_questions = []


        st.session_state.last_questions.append(
            question
        )


        st.session_state.last_questions = (
            st.session_state.last_questions[-20:]
        )


        with st.chat_message(
            "user"
        ):

            st.markdown(
                question
            )


        # -------------------------------------------------
        # KNOWLEDGE SEARCH
        # -------------------------------------------------

        results = knowledge_search(
            question
        )


        knowledge = ""


        for result in results:

            filename = result.get(
                "file",
                "Unknown"
            )

            text = result.get(
                "text",
                ""
            )


            knowledge += (
                f"\nFILE: {filename}\n"
                f"{text[:2500]}\n"
            )


        # -------------------------------------------------
        # HUMAN ESCALATION CHECK
        # -------------------------------------------------

        human_words = [
            "human",
            "agent",
            "person",
            "customer care",
            "customer support",
            "talk to someone",
            "representative"
        ]


        wants_human = any(
            word in question.lower()
            for word in human_words
        )


        if wants_human:

            ticket = create_ticket(
                question
            )


            answer = (
                "👤 **Human support requested.**\n\n"
                f"Your support ticket **{ticket['ticket_id']}** "
                "has been created.\n\n"
                "A human support agent can review your issue."
            )


        else:

            # ---------------------------------------------
            # AI
            # ---------------------------------------------

            with st.chat_message(
                "assistant"
            ):

                with st.spinner(
                    "🤖 Thinking..."
                ):

                    answer = ask_ai(
                        question,
                        knowledge
                    )

                st.markdown(
                    answer
                )


        # -------------------------------------------------
        # DISPLAY ESCALATION RESPONSE
        # -------------------------------------------------

        if wants_human:

            with st.chat_message(
                "assistant"
            ):

                st.markdown(
                    answer
                )


        # -------------------------------------------------
        # SAVE AI MESSAGE
        # -------------------------------------------------

        st.session_state.messages.append(
            {
                "role":
                    "assistant",

                "content":
                    answer
            }
        )


        # -------------------------------------------------
        # LONG-TERM MEMORY
        # -------------------------------------------------

        save_memory(
            question,
            answer
        )


        st.rerun()


# =========================================================
# LONG-TERM MEMORY PANEL
# =========================================================

st.divider()


with st.expander(
    "🧠 Long-Term Memory"
):

    customer = get_memory()


    # SAFE CUSTOMER ID
    customer_id = customer.get(
        "customer_id",
        st.session_state.get(
            "customer_id",
            DEFAULT_CUSTOMER_ID
        )
    )


    customer_name = customer.get(
        "name",
        ""
    )


    st.write(
        f"**Customer ID:** "
        f"{customer_id}"
    )


    st.write(
        f"**Customer Name:** "
        f"{customer_name}"
    )


    questions = customer.get(
        "questions",
        []
    )


    if not isinstance(
        questions,
        list
    ):

        questions = []


    st.write(
        f"**Saved Questions:** "
        f"{len(questions)}"
    )


    if questions:

        st.markdown(
            "### Previous Questions"
        )


        for q in reversed(
            questions[-10:]
        ):

            st.markdown(
                f"- {q}"
            )


    else:

        st.info(
            "No previous questions saved yet."
        )


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div style="
        text-align:center;
        padding:25px;
        color:#777;
    ">
    🤖 Vimala AI • Long-Term Memory ON
    </div>
    """,
    unsafe_allow_html=True
)