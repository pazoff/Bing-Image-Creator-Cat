from .BIC import ImageGen
from cat.mad_hatter.decorators import tool, hook, plugin
from cat.mad_hatter.plugin import Plugin as myplugin
from pydantic import BaseModel
from typing import Dict
import threading
import os
from datetime import datetime
import time
import uuid

# Define settings schema using Pydantic for the Cat plugin
class BingImageCreatorCatSettings(BaseModel):
    # Bing Cookie
    bing_Cookie: str
    prompt_suggestion: bool = True
    image_generation_in_the_background: bool = False
    enable_image_generation_tool: bool = False # Disable/Enable plugin required after changing the option



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
        
        # Save the images
        if image_links:
            try:
                # Remove invalid characters and replace spaces
                cleaned_prompt = ''.join(c if c.isalnum() or c in ['-', '_'] else '_' for c in prompt)

                # Limit the length of the filename
                max_filename_length = 200
                cleaned_prompt = cleaned_prompt[:max_filename_length]
                
                random_str = str(uuid.uuid4())
                destination_filename = cleaned_prompt + random_str[:4]
                full_path = "/app/cat/data/BICC/"
                if not os.path.exists(full_path):
                    os.makedirs(full_path)
                destination_path = os.path.join(full_path, "bicc_" + datetime.now().strftime("%Y-%m-%d"))
                image_generator.save_images(image_links, destination_path, file_name = destination_filename)
                print(f"{download_count} images saved to {destination_path}")
                
            except Exception as err:
                    print(f"Error saving the images to {destination_path}: {err}")

        # Generate <img> tags
        img_tags = ""
        for link in image_links[:download_count]:
            img_tags += f'<img src="{link}">\n'
        try:
            img_output_HTML_file = f"{destination_path}/images_tags.html"
            with open(img_output_HTML_file, "a", encoding="utf-8") as img_file:
                img_file.write(img_tags)
        except Exception as err:
            print(f"Error saving the images tags to {destination_path}: {err}")

        # Return the generated <img> tags
        return img_tags

    except Exception as e:
        b_error = (f"An error occurred: {str(e)}.<br>If the error persists you can check if your Bing Cookie is still valid: https://github.com/Mazawrath/BingImageCreator#getting-authentication")
        return b_error


def generate_Bing_images(prompt, cat):
    try:
        # Load the plugin settings
        settings = cat.mad_hatter.get_plugin().load_settings()
        bing_Cookie = settings.get("bing_Cookie")
        prompt_suggestion = settings.get("prompt_suggestion")
        image_generation_in_the_background = settings.get("image_generation_in_the_background")
        enable_image_generation_tool = settings.get("enable_image_generation_tool")
        download_count = 4  # Number of images to include in <img> tags
        
        if prompt_suggestion == None:
            prompt_suggestion = True

        if image_generation_in_the_background is None:
            image_generation_in_the_background = False

        if enable_image_generation_tool is None:
            enable_image_generation_tool = False

        # Check for a Bing Cookie
        if (bing_Cookie is None) or (bing_Cookie == ""):
            no_bing_cookie = 'Missing Bing Cookie in the plugin settings. How to get the Bing Cookie: https://github.com/Mazawrath/BingImageCreator#getting-authentication'
            return no_bing_cookie

        # Record the start time
        start_time = time.time()

        image_tags = generate_img_tags(bing_Cookie, prompt, download_count)

        # Record the end time
        end_time = time.time()

        # Calculate the execution time in seconds
        execution_time_seconds = end_time - start_time

        # Convert the execution time to minutes
        execution_time_minutes = execution_time_seconds / 60

        if image_generation_in_the_background:
            in_background = "[Threading]"
        else:
            in_background = ""

        print(f"{in_background}Bing images generation done in {execution_time_minutes:.2f} minutes - {execution_time_seconds:.2f} seconds.")

        if image_tags is not None:
            generation_message = f"<br>Generation took {execution_time_minutes:.2f} minutes - {execution_time_seconds:.2f} seconds."
            if image_generation_in_the_background and enable_image_generation_tool == False:
                cat.send_ws_message(content=f"Bing images generated on: <b>{prompt}</b>{generation_message}", msg_type='chat')
                cat.send_ws_message(content=image_tags, msg_type='chat')
                if prompt_suggestion:
                    related_image_prompt(prompt, cat)
            return image_tags + generation_message

    except Exception as e:
        # Handle the exception
        error_message = f"An error occurred: {str(e)}"
        print(error_message)
        return error_message



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
        image_generation_in_the_background = settings.get("image_generation_in_the_background")
        
        if prompt_suggestion == None:
            prompt_suggestion = True

        if image_generation_in_the_background == None:
            image_generation_in_the_background = False

        # Remove the asterisk
        message = message[:-1]

        print("Generating Bing images based on the prompt " + message)
        cat.send_ws_message(content='Generating Bing images based on the prompt ' + message + ' ...', msg_type='chat_token')

        if image_generation_in_the_background:
            t1 = threading.Thread(target=generate_Bing_images, args=(message, cat))
            t1.start()
            return {"output": "Generating Bing images in the background. The images will be sent to you when they are ready."}

        
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

# Load settings
this_plugin = myplugin("/app/cat/plugins/Bing-Image-Creator-Cat")
settings = this_plugin.load_settings()
enable_image_generation_tool = settings.get("enable_image_generation_tool")
if enable_image_generation_tool == None:
    enable_image_generation_tool = False


if enable_image_generation_tool:

    @tool(return_direct=True)
    def generate_images(tool_input, cat): # 
        """Useful to generate images. This tool generate images based on the user prompt.
         Input is a string.""" # 

        # Load settings
        settings = cat.mad_hatter.get_plugin().load_settings()
        prompt_suggestion = settings.get("prompt_suggestion")

        if prompt_suggestion == None:
            prompt_suggestion = True

        cat.send_ws_message(content='Generating Bing images based on the prompt ' + tool_input + ' ...', msg_type='chat_token')
        generated_images = generate_Bing_images(tool_input,cat)
        if generated_images:
            if prompt_suggestion:
                t3 = threading.Thread(target=related_image_prompt, args=(tool_input, cat))
                t3.start()

        return generated_images