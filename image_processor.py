import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from config import Config
import requests

client = OpenAI(api_key=Config.OPENAI_API_KEY)

def encode_image_to_base64(image_file):
    """Convert uploaded image file to base64 string"""
    image_file.seek(0)
    image_data = image_file.read()
    return base64.b64encode(image_data).decode('utf-8')

def decode_base64_to_image(base64_string):
    """Convert base64 string back to image bytes"""
    return base64.b64decode(base64_string)

def detect_dog_breed(image_base64):
    """
    Use GPT-4 Vision to analyze human face and suggest matching dog breed
    Returns the suggested dog breed name
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at analyzing human faces and matching them to dog breeds based on facial features, bone structure, and overall appearance. Provide only the dog breed name, nothing else."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this human headshot and determine which dog breed would most closely match this person's facial features. Consider factors like face shape, eye spacing, nose structure, and overall bone structure. Respond with only the breed name (e.g., 'Golden Retriever', 'German Shepherd', 'Bulldog')."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=50
        )
        
        breed = response.choices[0].message.content.strip()
        return breed
    except Exception as e:
        print(f"Error detecting breed: {e}")
        return "Mixed Breed"  # Default fallback

def generate_single_image(prompt):
    """
    Generate a single image using DALL-E 3
    """
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        # Download the generated image
        image_url = response.data[0].url
        
        # Fetch the image and convert to base64
        img_response = requests.get(image_url)
        img_data = img_response.content
        return base64.b64encode(img_data).decode('utf-8')
    except Exception as e:
        print(f"Error generating image: {e}")
        raise

def generate_transition_images(original_image_base64, breed, transition_count=2):
    """
    Generate transition images from human to dog
    Returns: (transition_1, transition_2, final_dog_image) as base64 strings
    """
    # Create prompts for each transition stage
    # Note: These prompts describe the transformation since DALL-E 3 doesn't support reference images
    prompts = [
        f"Professional portrait photography of a human face with subtle {breed} dog characteristics - slightly elongated snout, pointier ears, and dog-like expressive eyes. The person still looks human but with gentle canine features. High quality, photorealistic, studio lighting.",
        f"Portrait showing a person mid-transformation into a {breed} dog - more pronounced dog features with a longer snout, floppy or pointed ears matching the breed, and fur texture beginning to appear on the face and neck. Still maintains human-like proportions and expression. Photorealistic style.",
        f"Beautiful professional portrait of a {breed} dog with expressive eyes and personality, captured in high quality photography. The dog has a friendly, approachable expression that would match a human portrait. Studio lighting, photorealistic, detailed fur texture."
    ]
    
    # Generate all images in parallel using multithreading
    results = {}
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all generation tasks
        future_to_prompt = {
            executor.submit(generate_single_image, prompt): idx 
            for idx, prompt in enumerate(prompts)
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_prompt):
            idx = future_to_prompt[future]
            try:
                image_base64 = future.result()
                results[idx] = image_base64
            except Exception as e:
                print(f"Error generating image {idx}: {e}")
                # Return original image as fallback
                results[idx] = original_image_base64
    
    # Return in order: transition_1, transition_2, final
    return (
        results.get(0, original_image_base64),
        results.get(1, original_image_base64),
        results.get(2, original_image_base64)
    )
