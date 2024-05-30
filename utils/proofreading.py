import time
import google
import google.generativeai as genai
from utils import settings
from utils.console import print_substep
from tqdm.auto import tqdm


genai.configure(api_key=settings.config["ai"]["gemini_api_key"])
model = genai.GenerativeModel('gemini-pro')

prompt = """Can you please proof read this text while keeping the context the same.
Only respond with the proofread text.
If any part of the text wasn't human understandable remove it.
Here it is:
"""


def proofread_post(post):
    proofread_post = []
    print_substep("Proofreading post...")
    for post_part in tqdm(post):
        succeeded = False
        while not succeeded:
            try:
                proofread_post_part = model.generate_content(prompt + post_part)
            except google.api_core.exceptions.ResourceExhausted:
                print_substep(
                    " Resource Exhausted when proofreading the post. Sleeping for a few seconds...",
                    style="bold red"
                )
                time.sleep(62)
                proofread_post_part = model.generate_content(prompt + post_part)
                # time.sleep(1)
        
        try:
            proofread_post_part = proofread_post_part.text
            # print("Text:", proofread_post_part)
        except:
            # print("Data:", proofread_post_part.prompt_feedback)
            proofread_post_part = post_part
            # print("Original Text:", proofread_post_part)
        proofread_post.append(proofread_post_part)
    return proofread_post