import asyncio
from time import time
import streamlit.components.v1 as components
import streamlit as st
from jinja2 import Environment, FileSystemLoader
import httpx
import os
from dotenv import load_dotenv

load_dotenv()
AIR_KEY = os.getenv('AIR')
QnA = os.getenv('baseURL_QnA')
Snaps = os.getenv('base_Snaps')

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

async def fetch_QnA(out, idx=0):
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
    - Records stashed as a list with key 'res' in dict 'out'. 
    """
    IDs = DB_IDs[idx:idx+3]
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

    item = {}
    item["expected"] = expected
    item["pre_lib"] = pre_lib
    item["post_lib"] = post_lib
    item["explanation"] = explanation

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
st.write(AirCRUD_QnA(DB_IDs[0:3]))
print("IO in regular mode took {:.2f} secs.".format(time()-start))

"""
This part uses async IO to fetch contents.
"""
st.subheader("Asynchronus IO:")
out = {'res': None}
start = time()
asyncio.run(fetch_QnA(out))
st.write(out)
print("IO in async mode took {:.2f} secs.".format(time()-start))

"""
Plug-in the Q&A items 
"""
st.subheader("Templated Data")
env = Environment(loader=FileSystemLoader(os.path.join(os.getcwd(), "templates")))
qna_template = env.get_template('qna.html')
web_page = qna_template.render(quiz=[reframe_question(qna["fields"]) for qna in out["res"]])
st.text_area(web_page, height=10)

# Write HTML with CSS
st.subheader("REST HTML")
components.html(web_page, height=900)