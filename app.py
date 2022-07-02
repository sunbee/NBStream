import asyncio
from email.mime import base
from time import time
import streamlit.components.v1 as components
import streamlit as st
from jinja2 import Environment, FileSystemLoader
import httpx
import os
import base64
from dotenv import load_dotenv

load_dotenv()
AIR_KEY = os.getenv('AIR')
QnA = os.getenv('baseURL_QnA')
Snaps = os.getenv('base_Snaps')

"""
This is how many slides are downloaded at a time to render in gallery.
The number of slides show at a time (typically 3) must be less than 
or equal to this number.
"""
SIZE_OF_GALLERY = 5  

"""
Running Slideshow:
We display 3 slides at one time. To advance the slide-deck, 
we need to stash away the index of the start slide and
increment or decrement to forward or rewind the deck. 
But the entire code is run when any widget changes state, 
so the variable where the index is stored will be reset.
How to persist a variable in a way beyond the refresh?
For this, we use session state.
**Session state gives us a way to persist information 
across page-refreshes and the information is then tied
to a client session.**
"""
if 'idx' not in st.session_state:
    st.session_state["idx"] = 0

def AirCRUD_IDs(filterByFormula=None, fields=None):
    """
    Retrieve only IDs upto a specified maximum no. for records 
    from the question bank that match optional filter criteria.  
    The filter formula must be url-encoded and AirTable-supported. 
    TODO: Amend to use offset for table with over 100 records.
    Args: Ref. AirTable API docs and [formula](https://support.airtable.com/hc/en-us/articles/203255215-Formula-Field-Reference).
    """
    headers = {"Authorization": f"Bearer {AIR_KEY}"}
    params = {}
    if fields:
        params["fields"] = fields
    if filterByFormula:
        params["filterByFormula"] = filterByFormula

    endpoint = QnA

    r = httpx.get(url=endpoint, headers=headers, params=params)
    print(r.url)
    r.raise_for_status()

    return [item.get("id") for item in r.json().get("records")]

def AirCRUD_QnA(record_IDs):
    """
    Retrieve records from AirTable backend with a list of IDs.
    Args:
    - record_IDs is a list of AirTable record IDs
    Return:
    - A list of dicts., each dict bearing a single database record
    """
    headers = {"Authorization": f"Bearer {AIR_KEY}"}

    records = []
    for record_ID in record_IDs:
        endpoint = QnA + record_ID
        r = httpx.get(url=endpoint, headers=headers)
        print(r.url)
        r.raise_for_status()
        records.append(r.json())

    return records

async def AirCRUD_QnAx(record_IDs):
    """
    Retrieve with async. We will query the DB to retrieve content by ID.
    Fetching content requires multiple API calls, one for each record ID.
    The calls can be made concurrent or sequentially. We use async to make
    calls concurrently and speed up the operation.
    This requires:
    1. The worker with httpx async client (this function)
    2. The wrapper with asyncio gather
    3. The event loop from asyncio
    Args:
    - record_IDs is a list of DB (AirTable) IDs
    Return:
    - A list of dicts, each dict bearing a record from DB

    """
    headers = {"Authorization": f"Bearer {AIR_KEY}"}

    records = []
    async with httpx.AsyncClient() as client:
        for record_ID in record_IDs:
            endpoint = QnA + record_ID       
            r = await client.get(url=endpoint, headers=headers)
            print(f"URL as {r.url}")
            r.raise_for_status()
            records.append(r.json())

    return records

async def fetch_QnA(out, idx=0, num=SIZE_OF_GALLERY):
    """
    Wrap around the async worker with asyncio gather.
    Note that the worker returns a value and gather 
    is the appropriate method from asyncio to use
    in that case. However, the wrapper must have a 
    container in outside scope to stash data in instead
    of returning a value.
    Args:
    - out is a dict with a key named 'res' to hold the query result
    - idx is an int specifying the start index in a range to query from
    Return:
    - Records stashed in a list under key 'res' in dict 'out'. 
    """
    IDs = DB_IDs[idx:idx+num]
    contents = await asyncio.gather(AirCRUD_QnAx(IDs), return_exceptions=True)
    out["res"] = contents[0]
    
def reframe_question(qna_body):
    """
    Convert from dict returned by query to dict for HTML template for presentation.
    This allows plugging-in the data got from DB to template.
    Args:
    - qna_body is a dict representing one mad-lib, structured per DB schema.
    Return:
    - A dict structured in line with the HTML template
    """
    expected = qna_body.get("answer")[0]
    pre_lib, _, post_lib = qna_body.get("question").partition("___")
    explanation = qna_body.get("explanation")
    snapURL = qna_body.get("url (from Snaps)")[0]

    item = {}
    item["expected"] = expected
    item["pre_lib"] = pre_lib
    item["post_lib"] = post_lib
    item["explanation"] = explanation
    item["snapURL"] = snapURL

    return item

# Title the page
st.title("NBS Quiz")
st.header("Narada Bhakti Sutra")

"""
This part gets DB IDs (upto max limit imposed by AirTable API unless offset used)
"""
st.subheader("Async AirTable: What's in DB?")
DB_IDs = AirCRUD_IDs() # Get IDs of all records in QuestionBank
st.write(DB_IDs)

"""
This part uses regular IO to fetch contents.
"""
st.subheader("Synchronus IO:")
start = time()
st.write(AirCRUD_QnA(DB_IDs[0:SIZE_OF_GALLERY]))
print("IO in regular mode took {:.2f} secs.".format(time()-start))

"""
This part uses async IO to fetch contents.
"""
st.subheader("Asynchronus IO:")
idx = st.session_state["idx"]
out = {'res': None}
start = time()
asyncio.run(fetch_QnA(out, idx=idx))
st.write(out)
print("IO in async mode took {:.2f} secs.".format(time()-start))

"""
Manage slideshow
"""
number_items = len(DB_IDs)
start_no_further_than = number_items - 5
def rrwnd():
    st.session_state["idx"] = 0
def rwnd():
    if st.session_state["idx"] > 0:
        st.session_state["idx"] -= 1
        print("Decremented your session index to {}".format(st.session_state["idx"]))
def fwd():
    if st.session_state["idx"] < start_no_further_than:
        st.session_state["idx"] += 1
        print("Incremented your session index to {}".format(st.session_state["idx"]))
def ffwd():
    st.session_state["idx"] = start_no_further_than

with st.container():
    console = st.columns([1,1,7,1,1])
    with console[0]:
        st.button(label="<<", on_click=rrwnd)
    with console[1]:
        st.button(label="<", on_click=rwnd)
    with console[3]:
        st.button(label=">", on_click=fwd)
    with console[4]:
        st.button(label=">>", on_click=ffwd)

"""
Plug-in the Q&A items 
"""
env = Environment(loader=FileSystemLoader(os.path.join(os.getcwd(), "templates")))
qna_template = env.get_template('qna.html')
web_page = qna_template.render(quiz=[reframe_question(qna["fields"]) for qna in out["res"]])
components.html(web_page, width=960,height=450)


