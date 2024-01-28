from .BIC import ImageGen
from cat.mad_hatter.decorators import tool, hook, plugin
from pydantic import BaseModel
from typing import Dict
import threading

# Define settings schema using Pydantic for the Cat plugin
class BingImageCreatorCatSettings(BaseModel):
    # Bing Cookie
    bing_Cookie: str
    prompt_suggestion: bool = True


# Plugin function to provide the Cat with the settings schema
@plugin
def settings_schema():
    return BingImageCreatorCatSettings.schema()

def generate_img_tags(auth_cookie, prompt, download_count, auth_cookie_SRCHHPGUSR=None):
    try:
        # Instantiate ImageGen
        image_generator = ImageGen(auth_cookie, auth_cookie_SRCHHPGUSR=None)

        # Fetch image links
        image_links = image_generator.get_images(prompt)

        # Generate <img> tags
        img_tags = ""
        for link in image_links[:download_count]:
            img_tags += f'<img src="{link}">\n'

        # Return the generated <img> tags
        return img_tags

    except Exception as e:
        b_error = (f"An error occurred: {str(e)}.<br>If the error persists you can check if your Bing Cookie is still valid: https://github.com/Mazawrath/BingImageCreator#getting-authentication")
        return b_error

def generate_Bing_images(prompt,cat):

    # Load the plugin settings
    settings = cat.mad_hatter.get_plugin().load_settings()
    bing_Cookie = settings.get("bing_Cookie")
    download_count = 4  # Number of images to include in <img> tags

    # Check for a Bing Cookie
    if (bing_Cookie is None) or (bing_Cookie == ""):
        no_bing_cookie = 'Missing Bing Cookie in the plugin settings. How to get the Bing Cookie: https://github.com/Mazawrath/BingImageCreator#getting-authentication'
        return no_bing_cookie

    image_tags = generate_img_tags(bing_Cookie, prompt, download_count)

    if image_tags is not None:
        return image_tags

def related_image_prompt(prompt, cat):
    try:
        related_prompt = cat.llm(f"Write 3 prompts for Bing image creator, very diffrent from each other, based on: {prompt}. Every prompt must end with *<br><br>")
        if related_prompt:
            cat.send_ws_message(content=f"<b>You may also try:</b><br>{related_prompt}", msg_type='chat')
    except Exception as e:
        print(f"Error in related_image_prompt: {e}")


# Hook function for fast reply generation
@hook(priority=5)
def agent_fast_reply(fast_reply, cat) -> Dict:
    return_direct = False

    # Get user message from the working memory
    message = cat.working_memory["user_message_json"]["text"]

    # Check if the message ends with an asterisk
    if message.endswith('*'):
        # Load settings
        settings = cat.mad_hatter.get_plugin().load_settings()
        prompt_suggestion = settings.get("prompt_suggestion")
        if prompt_suggestion == None:
            prompt_suggestion = True

        # Remove the asterisk
        message = message[:-1]

        print("Generating Bing images based on the prompt " + message)
        cat.send_ws_message(content='Generating Bing images based on the prompt ' + message + ' ...', msg_type='chat_token')

        # Generate image with the provided prompt and 50 steps
        generated_images = generate_Bing_images(message,cat)

        if generated_images:
            
            if prompt_suggestion:
                t = threading.Thread(target=related_image_prompt, args=(message, cat))
                t.start()

            return {"output": generated_images}
        else:
            print("Image generation failed.")
            return {"output": "No image was generated!<br>If the error persists you can check if your Bing Cookie is still valid: https://github.com/Mazawrath/BingImageCreator#getting-authentication"}

    # Return fast reply if no image generation is requested
    return fast_reply