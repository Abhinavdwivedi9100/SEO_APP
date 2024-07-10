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
import re
import praw
from streamlit_tags import st_tags


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
        return 'Error', {}, f"Error fetching the webpage: {e}"

def get_openai_response(prompt, n=1):
    try:
        response = client.chat.completions.create(
            n=n,
            messages=[
                {"role": "system", "content": "You are a Search Engine Optimization Expert and know how to improve the title, meta-headers, and body to make the article rich and help it get search engine optimized."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o"
        )
        print(response.usage.prompt_tokens, response.usage.completion_tokens)
        return [response.choices[x].message.content for x in range(n)]
    except Exception as e:
        return [f"Error getting OpenAI response: {e}"]

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
    return get_openai_response(prompt)

def content_summarizer(content):
    prompt = f"""Act as a Social Media Account holder and create a Post for the social media platform from the {content} in under 2000 characters strictly. If there is more than one content or article, then take the topmost article. You should use the latest and trending keywords along with hashtags and emojis. Don't use markdowns. Don't use any links."""
    response = get_openai_response(prompt)
    return response[0]

def generate_keywords(content):
    if isinstance(content, tuple):
        content = ' '.join(content)
    return re.findall(r'#\w+', content)

def upload_to_instagram(username, password, image_data, caption):
    try:
        cl = Client()
        cl.login(username, password)
        with open("temp_image.jpg", "wb") as f:
            f.write(image_data)
        cl.photo_upload("temp_image.jpg", caption, extra_data={"custom_accessibility_caption": "hi all", "like_and_view_counts_disabled": 1, "disable_comments": 1})
        return True, "Post uploaded successfully!"
    except Exception as e:
        return False, f"An error occurred: {e}"

def post_to_facebook(api, caption, image_data):
    try:
        dogapi = fb.GraphAPI(api)
        dogapi.put_photo(image=image_data, message=caption)
        return True, "Post successful."
    except Exception as e:
        return False, f"An error occurred: {e}"

def initialize_reddit(client_id, client_secret, password, user_agent, username):
    return praw.Reddit(client_id=client_id, client_secret=client_secret, password=password, user_agent=user_agent, username=username)


def post_reply(reddit, submission_id, reply_text):
    try:
        submission = reddit.submission(id=submission_id)
        submission.reply(reply_text)
        print(f"Replied to submission with ID: {submission_id}")
    except Exception as e:
        print(f"Error posting reply: {e}")

def break_keywords(keywords):
    return keywords.split()

def search_questions(reddit, keyword_pieces, subreddit_name):
    query = ' OR '.join(keyword_pieces)
    try:
        results = list(reddit.subreddit(subreddit_name if subreddit_name else 'all').search(query, sort='relevance', time_filter='all', limit=limit))
        questions = [{'id': submission.id, 'title': submission.title, 'url': submission.url, 'score': submission.score, 'subreddit': submission.subreddit.display_name} for submission in results]
        return questions
    except Exception as e:
        print(f"Error searching in r/{subreddit_name}: {e}")
        return []

def generate_answer(openai_client, question_title, context):
    try:
        system_message = (
            "You are a highly knowledgeable and helpful assistant. "
            "Analyze the given context thoroughly. "
            "If it's a discussion, engage thoughtfully and contribute valuable insights. "
            "If it's a question, provide a comprehensive answer addressing all relevant points. "
            "Always strive to give the best possible response."
        )
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Here's the topic or question. Provide a relevant and brief answer in about 150 words to the following:\n\n{question_title}"}
        ]
        if context:
            messages.append({"role": "user", "content": f"Additional context:\n\n{context}"})
        response = openai_client.chat.completions.create(model="gpt-4o", messages=messages, max_tokens=4096, temperature=0.1)
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating answer: {e}")
        return ""


def display_results(questions):
    st.write("\nQuestions:\n")
    for question in questions:
        st.write(f"Title: {question['title']}")
        st.write(f"Score: {question['score']}")
        st.write(f"URL: {question['url']}")
        st.write(f"Subreddit: r/{question['subreddit']}\n")

# *****************************************************************************

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
            st.session_state['summarized_content'] = summarized_content             
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

# Section for uploading to Reddit
if 'summarized_content' in st.session_state:
    st.title("Reddit Post Auto-Upload")
    client_id = st.text_input("Reddit Client ID")
    client_secret = st.text_input("Reddit Client Secret", type="password")
    reddit_password = st.text_input("Reddit Password", type="password")
    user_agent = st.text_input("Reddit User Agent")
    reddit_username = st.text_input("Reddit Username")

    subreddits = ["all", "BestOf", "India", "OutOfTheLoop", "popular"]
    
    if 'selected_subreddits' not in st.session_state:
        st.session_state['selected_subreddits'] = []

    selected_subreddits_from_dropdown = st.multiselect("Select subreddits to search", options=subreddits, default=[])
    new_subreddits = st_tags(label='Add new subreddits:', text='Press enter to add more', value=[], suggestions=subreddits)
    st.session_state['selected_subreddits'] = list(set(selected_subreddits_from_dropdown + new_subreddits))
    st.write("Selected subreddits:", st.session_state['selected_subreddits'])

    try:
        keywords = generate_keywords(st.session_state['summarized_content'])
        if not keywords:
            raise ValueError("No keywords generated.")
        st.write("Original keywords:", keywords)
    except Exception as e:
        st.error(f"Error generating keywords: {e}")

    if 'selected_keywords' not in st.session_state:
        st.session_state['selected_keywords'] = []

    try:
        selected_from_dropdown = st.multiselect("Select keywords to search", options=keywords if keywords else [], default=[])
        new_keywords = st_tags(label='Add new keywords:', text='Press enter to add more', value=[], suggestions=keywords if keywords else [])
        st.session_state['selected_keywords'] = list(set(selected_from_dropdown + new_keywords))
        st.write("Selected keywords:", st.session_state['selected_keywords'])
    except Exception as e:
        st.error(f"Error handling keywords: {e}")

    limit = st.number_input("Number of results to fetch", min_value=1, max_value=100, value=5)

    if st.button("Search and Post"):
        if client_id and client_secret and reddit_password and user_agent and reddit_username and st.session_state['selected_keywords'] and st.session_state['selected_subreddits']:
            try:
                reddit = initialize_reddit(client_id, client_secret, reddit_password, user_agent, reddit_username)
                questions = []
                for keyword in st.session_state['selected_keywords']:
                    keyword_pieces = break_keywords(keyword)
                    for subreddit in st.session_state['selected_subreddits']:
                        st.write(f"\nSearching for questions with keywords: {keyword_pieces} in r/{subreddit}")
                        subreddit_questions = search_questions(reddit, keyword_pieces, subreddit)
                        if not subreddit_questions:
                            st.write(f"No results found for subreddit: {subreddit}")
                            continue
                        questions.extend(subreddit_questions)
                    if len(questions) >= limit:
                        break
                if not questions:
                    st.write("No questions found.")
                else:
                    questions = sorted(questions, key=lambda x: x['score'], reverse=True)
                    for question in questions[:limit]:
                        submission_id = question['id']
                        question_title = question['title']
                        context = None
                        answer = generate_answer(client, question_title, context)
                        if answer:
                            st.write(f"**Question:** {question_title}")
                            st.write(f"**Answer:** {answer}")
                            if question == questions[0]:
                                success, message = post_reply(reddit, submission_id, answer)
                                if success:
                                    st.success(message)
                                else:
                                    st.error(message)
                        else:
                            st.write(f"Failed to generate answer for question: {question_title}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

# import streamlit as st
# import requests
# from bs4 import BeautifulSoup
# import os
# from openai import OpenAI
# from instagrapi import Client
# from time import sleep
# from requests.exceptions import HTTPError
# import openai
# import pandas as pd
# import os
# import facebook as fb
# from dotenv import load_dotenv
# load_dotenv()

# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# # Function to scrape webpage content.
# def scrape_webpage(url):
#     try:
#         response = requests.get(url)
#         response.raise_for_status()  

#         soup = BeautifulSoup(response.content, 'html.parser')

#         title = soup.title.string if soup.title else 'No title found'

#         meta_headers = {meta.attrs['name']: meta.attrs['content'] for meta in soup.find_all('meta') if 'name' in meta.attrs and 'content' in meta.attrs}

#         body = soup.body.get_text(separator='\n') if soup.body else 'No body content found'

#         return title, meta_headers, body
#     except requests.exceptions.RequestException as e:
#         return None, f"Error fetching the webpage: {e}"

# # Function to get optimized content from OpenAI
# def get_openai_response(prompt, n=1):
#     response = client.chat.completions.create(
#         n = n,
#         messages = [
#             {"role":"system","content": "You are a Search Engine Optimization Expert and knows how to improve the title, meta-headers and body, so as to make the article rich and help it to get search engine optimized."},
#             {"role": "user", "content": prompt}
#         ],
#         model = "gpt-4o",
#     )
#     print(response.usage.prompt_tokens, response.usage.completion_tokens)
#     return [response.choices[x].message.content for x in range(n)]

# def default_function(title, meta_headers, body):
#     prompt = f"""Act as a Search Engine Optimization Expert. You can rate the current article in percentage and also rate the optimized content.

#     Given the following article content:
#     Title: {title}
#     Meta Headers: {meta_headers}
#     Body: {body}
    
#     Provide the optimized title, meta headers, and body content in the following format:
#     Title: 'title'
#     Meta Headers: 'meta_headers'
#     Body: 'body'
#     Rating(Original content): 'rating of original content'
#     Rating(Optimized content): 'rating of optimized content'
#     **Don't add any sort of 'Note' from your side in the end.**
#     """
#     response = get_openai_response(prompt)
#     return response

# # Function to summarize content
# def content_summarizer(content):
#     prompt = f"""Act as a Social Media Account holder and can create a Post for the social media platform from the {content} in under 2000 characters strictly.If there there more than one content or article then take the topmost article. You should use latest and trending keywords along with hashtags. Don't use markdowns. Dont use any links.
#     """
#     final_response = get_openai_response(prompt)
#     print(final_response)
#     return final_response[0]    

# # Function to upload to Instagram
# def upload_to_instagram(username, password, image_data, caption):
#     try:
#         cl = Client()
#         cl.login(username, password)

#         # Write image data to a temporary file
#         with open("temp_image.jpg", "wb") as f:
#             f.write(image_data)

#         # Upload photo with caption
#         media = cl.photo_upload(
#             "temp_image.jpg",
#             caption,
#             extra_data={
#                 "custom_accessibility_caption": "hi all",
#                 "like_and_view_counts_disabled": 1,
#                 "disable_comments": 1,
#             }
#         )

#         return True, "Post uploaded successfully!"
#     except Exception as e:
#         return False, f"An error occurred: {e}"

# # Function to post to Facebook
# def post_to_facebook(api, caption, image_data):
#     try:
#         # Initialize the Graph API with the access token
#         dogapi = fb.GraphAPI(api)
        
#         # Post a message with a link
#         dogapi.put_photo(image=image_data, message=caption)
        
#         print("Post successful.")
#         return True, "Post successful."
#     except Exception as e:
#         return False, f"An error occurred: {e}"  

# # Streamlit App
# st.title("Content Optimizer for SEO and Social Media Posts")

# # Section for scraping and optimizing webpage
# url = st.text_input("Enter the URL of the webpage you want to Optimize:")

# if url:
#     title, meta_headers, body = scrape_webpage(url)

#     if title and body:
#         st.subheader("Original Title")
#         st.write(title)

#         st.subheader("Original Body Content")
#         st.text_area("Original Body", body, height=300)

#         if st.button("Optimize for SEO"):
#             optimized_content = default_function(title, meta_headers, body)
            
#             st.subheader("Optimized Content")
#             st.write(optimized_content)
        
#         if st.button("Optimize for Social Media"):
#             summarized_content = content_summarizer(body)
#             st.session_state['summarized_content'] =summarized_content             
#             st.subheader("Summarized Content for Social Media")
#             st.write(summarized_content)

# # Section for uploading to Instagram
# if 'summarized_content' in st.session_state:
#     st.title("Instagram Post Auto-Upload")

#     username = st.text_input("Instagram Username")
#     password = st.text_input("Instagram Password", type="password")

#     uploaded_file = st.file_uploader("Choose an image for Instagram...", type=["jpg", "jpeg", "png"])

#     if st.button("Upload to Instagram"):
#         if username and password and uploaded_file:
#             try:
#                 # Read image data
#                 image_data = uploaded_file.read()

#                 success, message = upload_to_instagram(username, password, image_data, st.session_state['summarized_content'])
                
#                 if success:
#                     st.success(message)
#                 else:
#                     st.error(message)
#             except Exception as e:
#                 st.error(f"An error occurred: {e}")
#         else:
#             st.warning("Please fill out all fields.")

# # Section for uploading to Facebook
# if 'summarized_content' in st.session_state:
#     st.title("Facebook Post Auto-Upload")

#     api_token = st.text_input("Facebook API Token", type="password")

#     fb_uploaded_file = st.file_uploader("Choose an image for Facebook...", type=["jpg", "jpeg", "png"])

#     if st.button("Upload to Facebook"):
#         if api_token and fb_uploaded_file:
#             try:
#                 fb_image_data = fb_uploaded_file.read()

#                 success, message = post_to_facebook(api_token, st.session_state['summarized_content'], fb_image_data)
                
#                 if success:
#                     st.success(message)
#                 else:
#                     st.error(message)
#             except Exception as e:
#                 st.error(f"An error occurred: {e}")
#         else:
#             st.warning("Please fill out all fields.")
# else:
#     st.warning("Please enter a valid URL.")
