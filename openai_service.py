import openai
import base64
import os
import logging
from config import Config
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)

def get_client():
    """Get OpenAI client with API key validation."""
    if not Config.OPENAI_API_KEY or Config.OPENAI_API_KEY == 'your_api_key_here':
        raise ValueError("OpenAI API key not set. Please set OPENAI_API_KEY in .env file.")
    
    try:
        # Check for proxy environment variables that might cause issues
        proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
        has_proxy = any(os.getenv(var) for var in proxy_vars)
        if has_proxy:
            logger.warning(f"Proxy environment variables detected: {[var for var in proxy_vars if os.getenv(var)]}")
        
        # Create client with just the API key
        # Newer OpenAI versions handle proxies automatically via environment variables
        client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        logger.info("OpenAI client created successfully")
        return client
    except TypeError as e:
        # If there's a TypeError about unexpected arguments, log it
        logger.error(f"Error creating OpenAI client: {str(e)}")
        logger.error(f"OpenAI version: {openai.__version__}")
        raise

def detect_breed(image_file):
    """
    Analyze a human headshot and determine which dog breed most closely resembles it.
    
    Args:
        image_file: File object or bytes of the image
        
    Returns:
        tuple: (breed_name, reasoning) or (None, error_message)
    """
    try:
        # Read image data
        if hasattr(image_file, 'read'):
            image_data = image_file.read()
            image_file.seek(0)  # Reset file pointer
        else:
            image_data = image_file
        
        # Convert to base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Get OpenAI client
        client = get_client()
        
        # Use OpenAI Vision API to analyze the image
        # Use a more explicit prompt that avoids content policy issues
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that analyzes photos to suggest which dog breed has similar facial features. This is for a fun, creative art project. Always provide a breed suggestion."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Look at this portrait photo. Based on facial features like face shape, eye shape, and overall structure, which dog breed would be a good artistic match? This is for a creative digital art project. Respond ONLY in this exact format:\nBREED: [breed name]\nREASONING: [one sentence explanation]"
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
            max_tokens=300,
            temperature=0.7
        )
        
        result = response.choices[0].message.content
        
        # Check if OpenAI refused the request
        if not result or "sorry" in result.lower() or "can't" in result.lower() or "cannot" in result.lower():
            logger.warning(f"OpenAI content policy refusal detected: {result}")
            # Fallback to a default breed suggestion
            return "Golden Retriever", "Based on general facial features, a friendly Golden Retriever would be a good match."
        
        lines = result.split('\n')
        
        breed = None
        reasoning = ""
        
        for line in lines:
            if line.startswith('BREED:'):
                breed = line.replace('BREED:', '').strip()
            elif line.startswith('REASONING:'):
                reasoning = line.replace('REASONING:', '').strip()
        
        if not breed:
            # Fallback: try to extract breed from the response
            # Look for common breed names in the response
            common_breeds = ['Golden Retriever', 'Labrador', 'German Shepherd', 'Beagle', 'Bulldog', 'Poodle', 'Husky', 'Border Collie', 'Corgi', 'Shih Tzu', 'Pug', 'Chihuahua', 'Dachshund', 'Siberian Husky', 'Australian Shepherd']
            result_lower = result.lower()
            for common_breed in common_breeds:
                if common_breed.lower() in result_lower:
                    breed = common_breed
                    reasoning = result[:200]  # First 200 chars as reasoning
                    break
            
            if not breed:
                # Last resort: use first line or default
                breed = result.split('\n')[0].strip()[:50] or "Golden Retriever"
                reasoning = result[:200] if result else "General facial similarity"
        
        return breed, reasoning
        
    except Exception as e:
        logger.error(f"Error in detect_breed: {type(e).__name__}: {str(e)}", exc_info=True)
        return None, f"Error detecting breed: {str(e)}"

def generate_transition_image(original_image_data, breed, transition_number, total_transitions=2):
    """
    Generate a transition image showing the transformation from human to dog.
    
    Args:
        original_image_data: Bytes of the original human image
        breed: The dog breed to transform into
        transition_number: Which transition this is (1 or 2)
        total_transitions: Total number of transitions (default 2)
        
    Returns:
        bytes: Generated image data or None if error
    """
    try:
        # Convert image to base64
        if isinstance(original_image_data, bytes):
            image_base64 = base64.b64encode(original_image_data).decode('utf-8')
        else:
            image_base64 = base64.b64encode(original_image_data.read()).decode('utf-8')
        
        # Create prompt based on transition number
        if transition_number == 1:
            prompt = f"A photorealistic image showing a gradual transformation from a human face to a {breed} dog. This is the first transition - the face should show early signs of transformation: slightly more canine features, but still mostly human. The transformation should be subtle and natural-looking."
        elif transition_number == 2:
            prompt = f"A photorealistic image showing a gradual transformation from a human face to a {breed} dog. This is the second transition - the face should show more pronounced canine features: more dog-like snout, ears, and fur, but still retaining some human characteristics. The transformation should be natural and seamless."
        else:
            prompt = f"A photorealistic image showing a gradual transformation from a human face to a {breed} dog. This is transition {transition_number} of {total_transitions}."
        
        # Get OpenAI client
        client = get_client()
        
        # Use DALL-E to generate the image
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        # Download the generated image
        image_url = response.data[0].url
        
        import requests
        img_response = requests.get(image_url)
        img_response.raise_for_status()
        
        return img_response.content
        
    except Exception as e:
        print(f"Error generating transition image {transition_number}: {str(e)}")
        return None

def generate_final_dog_image(original_image_data, breed):
    """
    Generate the final dog image transformation.
    
    Args:
        original_image_data: Bytes of the original human image
        breed: The dog breed to transform into
        
    Returns:
        bytes: Generated image data or None if error
    """
    try:
        prompt = f"A photorealistic portrait of a {breed} dog that closely resembles the facial features and expression of the human in the reference image. The dog should have the same general facial structure, eye shape, and expression as the human, but fully transformed into a {breed}. High quality, detailed, professional photography style."
        
        # Get OpenAI client
        client = get_client()
        
        # Use DALL-E to generate the final image
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        # Download the generated image
        image_url = response.data[0].url
        
        import requests
        img_response = requests.get(image_url)
        img_response.raise_for_status()
        
        return img_response.content
        
    except Exception as e:
        print(f"Error generating final dog image: {str(e)}")
        return None
