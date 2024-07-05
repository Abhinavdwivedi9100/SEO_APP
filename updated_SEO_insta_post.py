import streamlit as st
import requests
from bs4 import BeautifulSoup
import os
from openai import OpenAI
from instagrapi import Client
from time import sleep
from requests.exceptions import HTTPError
import openai
import pandas as pd
import os
import facebook as fb
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Function to scrape webpage content.
def scrape_webpage(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  

        soup = BeautifulSoup(response.content, 'html.parser')

        title = soup.title.string if soup.title else 'No title found'

        meta_headers = {meta.attrs['name']: meta.attrs['content'] for meta in soup.find_all('meta') if 'name' in meta.attrs and 'content' in meta.attrs}

        body = soup.body.get_text(separator='\n') if soup.body else 'No body content found'

        return title, meta_headers, body
    except requests.exceptions.RequestException as e:
        return None, f"Error fetching the webpage: {e}"

# Function to get optimized content from OpenAI
def get_openai_response(prompt, n=1):
    response = client.chat.completions.create(
        n = n,
        messages = [
            {"role":"system","content": "You are a Search Engine Optimization Expert and knows how to improve the title, meta-headers and body, so as to make the article rich and help it to get search engine optimized."},
            {"role": "user", "content": prompt}
        ],
        model = "gpt-4o",
    )
    print(response.usage.prompt_tokens, response.usage.completion_tokens)
    return [response.choices[x].message.content for x in range(n)]

def default_function(title, meta_headers, body):
    prompt = f"""Act as a Search Engine Optimization Expert. You can rate the current article in percentage and also rate the optimized content.

    Given the following article content:
    Title: {title}
    Meta Headers: {meta_headers}
    Body: {body}
    
    Provide the optimized title, meta headers, and body content in the following format:
    Title: 'title'
    Meta Headers: 'meta_headers'
    Body: 'body'
    Rating(Original content): 'rating of original content'
    Rating(Optimized content): 'rating of optimized content'
    **Don't add any sort of 'Note' from your side in the end.**
    """
    response = get_openai_response(prompt)
    return response

# Function to summarize content
def content_summarizer(content):
    prompt = f"""Act as a Social Media Account holder and can create a Post for the social media platform from the {content} in under 2000 characters strictly.If there there more than one content or article then take the topmost article. You should use latest and trending keywords along with hashtags. Don't use markdowns. Dont use any links.
    """
    final_response = get_openai_response(prompt)
    print(final_response)
    return final_response[0]    

# Function to upload to Instagram
def upload_to_instagram(username, password, image_data, caption):
    try:
        cl = Client()
        cl.login(username, password)

        # Write image data to a temporary file
        with open("temp_image.jpg", "wb") as f:
            f.write(image_data)

        # Upload photo with caption
        media = cl.photo_upload(
            "temp_image.jpg",
            caption,
            extra_data={
                "custom_accessibility_caption": "hi all",
                "like_and_view_counts_disabled": 1,
                "disable_comments": 1,
            }
        )

        return True, "Post uploaded successfully!"
    except Exception as e:
        return False, f"An error occurred: {e}"

# Function to post to Facebook
def post_to_facebook(api, caption, image_data):
    try:
        # Initialize the Graph API with the access token
        dogapi = fb.GraphAPI(api)
        
        # Post a message with a link
        dogapi.put_photo(image=image_data, message=caption)
        
        print("Post successful.")
        return True, "Post successful."
    except Exception as e:
        return False, f"An error occurred: {e}"  

# Streamlit App
st.title("Content Optimizer for SEO and Social Media Posts")

# Section for scraping and optimizing webpage
url = st.text_input("Enter the URL of the webpage you want to Optimize:")

if url:
    title, meta_headers, body = scrape_webpage(url)

    if title and body:
        st.subheader("Original Title")
        st.write(title)

        st.subheader("Original Body Content")
        st.text_area("Original Body", body, height=300)

        if st.button("Optimize for SEO"):
            optimized_content = default_function(title, meta_headers, body)
            
            st.subheader("Optimized Content")
            st.write(optimized_content)
        
        if st.button("Optimize for Social Media"):
            summarized_content = content_summarizer(body)
            st.session_state['summarized_content'] =summarized_content             
            st.subheader("Summarized Content for Social Media")
            st.write(summarized_content)

# Section for uploading to Instagram
if 'summarized_content' in st.session_state:
    st.title("Instagram Post Auto-Upload")

    username = st.text_input("Instagram Username")
    password = st.text_input("Instagram Password", type="password")

    uploaded_file = st.file_uploader("Choose an image for Instagram...", type=["jpg", "jpeg", "png"])

    if st.button("Upload to Instagram"):
        if username and password and uploaded_file:
            try:
                # Read image data
                image_data = uploaded_file.read()

                success, message = upload_to_instagram(username, password, image_data, st.session_state['summarized_content'])
                
                if success:
                    st.success(message)
                else:
                    st.error(message)
            except Exception as e:
                st.error(f"An error occurred: {e}")
        else:
            st.warning("Please fill out all fields.")

# Section for uploading to Facebook
if 'summarized_content' in st.session_state:
    st.title("Facebook Post Auto-Upload")

    api_token = st.text_input("Facebook API Token", type="password")

    fb_uploaded_file = st.file_uploader("Choose an image for Facebook...", type=["jpg", "jpeg", "png"])

    if st.button("Upload to Facebook"):
        if api_token and fb_uploaded_file:
            try:
                fb_image_data = fb_uploaded_file.read()

                success, message = post_to_facebook(api_token, st.session_state['summarized_content'], fb_image_data)
                
                if success:
                    st.success(message)
                else:
                    st.error(message)
            except Exception as e:
                st.error(f"An error occurred: {e}")
        else:
            st.warning("Please fill out all fields.")
else:
    st.warning("Please enter a valid URL.")
