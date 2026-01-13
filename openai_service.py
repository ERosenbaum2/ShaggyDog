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
        
        # Use OpenAI Vision API to analyze the image with detailed physical characteristics
        # Enhanced prompt for more accurate breed matching
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert visual analyst specializing in matching human portraits to dog breeds for creative digital art projects. You analyze photos objectively based on observable physical characteristics. Your task is to examine the provided image and suggest the most appropriate dog breed match based on facial features, build, coloring, and other visible traits. This is for artistic transformation purposes."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """You are analyzing a portrait photograph. Look carefully at the image and identify the following observable physical characteristics:

REQUIRED ANALYSIS - Examine the image and note:
1. Face shape: (round, oval, square, long, heart-shaped, angular)
2. Eye characteristics: (shape, size, spacing - large/small, almond/round, wide-set/close-set)
3. Skin tone and coloring: (light, medium, dark, and any undertones visible)
4. Hair characteristics: (if visible: color, texture - curly/straight/wavy, length, style)
5. Facial structure: (cheekbone prominence, jawline shape, nose shape and size)
6. Build/physique: (if visible: athletic, stocky, lean, petite, large-framed)
7. Expression and energy: (friendly, serious, playful, calm, intense)
8. Overall proportions: (head size relative to visible body, facial feature proportions)

Based on these SPECIFIC characteristics you observe in THIS image, determine which dog breed would be the most accurate artistic match. Consider:
- Which breed has similar facial structure?
- Which breed has similar build/physique?
- Which breed has similar coloring (coat color matching skin/hair tone)?
- Which breed has similar energy/expression?
- Which breed has similar proportional features?

IMPORTANT: You MUST analyze the actual image provided. Look at the specific person in the photo and match them to an appropriate dog breed based on what you actually see.

Respond in EXACTLY this format (no other text):
BREED: [specific dog breed name - be precise, e.g., "Rottweiler" not just "dog"]
REASONING: [2-3 sentences describing the specific physical characteristics you observed in the image that led to this breed match, including face shape, build, coloring, etc.]

Example format:
BREED: Rottweiler
REASONING: The person has a strong, square jawline and athletic build similar to a Rottweiler. The darker skin tone matches the Rottweiler's black and tan coloring. The facial structure with prominent cheekbones and determined expression aligns with the breed's characteristic appearance."""
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
            max_tokens=500,
            temperature=0.5
        )
        
        result = response.choices[0].message.content
        logger.info(f"OpenAI breed detection raw response: {result[:500]}")  # Log first 500 chars
        
        # Check if OpenAI refused the request
        refusal_keywords = ["sorry", "can't", "cannot", "unable", "not able", "i'm not", "i cannot", "i can't"]
        is_refusal = not result or any(keyword in result.lower() for keyword in refusal_keywords)
        
        if is_refusal:
            logger.error(f"OpenAI content policy refusal detected. Full response: {result}")
            # Don't use fallback - return error so user knows something went wrong
            return None, f"Content policy restriction: {result[:100]}"
        
        lines = result.split('\n')
        
        breed = None
        reasoning = ""
        
        # Parse the response
        for line in lines:
            line = line.strip()
            if line.startswith('BREED:'):
                breed = line.replace('BREED:', '').strip()
                logger.info(f"Extracted breed: {breed}")
            elif line.startswith('REASONING:'):
                reasoning = line.replace('REASONING:', '').strip()
                logger.info(f"Extracted reasoning: {reasoning[:200]}")
        
        # If we didn't find BREED: line, try to extract from response
        if not breed:
            logger.warning("BREED: line not found in response, attempting extraction")
            # Look for common breed names in the response
            common_breeds = [
                'Golden Retriever', 'Labrador Retriever', 'Labrador', 'German Shepherd', 
                'Beagle', 'Bulldog', 'French Bulldog', 'Poodle', 'Husky', 'Siberian Husky',
                'Border Collie', 'Corgi', 'Pembroke Welsh Corgi', 'Shih Tzu', 'Pug', 
                'Chihuahua', 'Dachshund', 'Australian Shepherd', 'Rottweiler', 'Doberman',
                'Boxer', 'Great Dane', 'Mastiff', 'Saint Bernard', 'Bernese Mountain Dog',
                'Shiba Inu', 'Akita', 'Chow Chow', 'Dalmatian', 'Weimaraner'
            ]
            result_lower = result.lower()
            for common_breed in common_breeds:
                if common_breed.lower() in result_lower:
                    breed = common_breed
                    # Try to extract reasoning from nearby text
                    breed_index = result_lower.find(common_breed.lower())
                    reasoning = result[max(0, breed_index-50):breed_index+200].strip()
                    logger.info(f"Found breed '{breed}' in response text")
                    break
        
        # Final validation
        if not breed or len(breed) < 2:
            logger.error(f"Failed to extract valid breed from response: {result[:300]}")
            return None, f"Could not determine breed from analysis. Response: {result[:200]}"
        
        # Validate breed name (should be reasonable length and not contain refusal text)
        if len(breed) > 50 or any(keyword in breed.lower() for keyword in refusal_keywords):
            logger.error(f"Invalid breed extracted: {breed}")
            return None, "Invalid breed detected in response"
        
        logger.info(f"Successfully detected breed: {breed} with reasoning: {reasoning[:100]}")
        return breed, reasoning or f"Based on facial features and physical characteristics observed in the image."
        
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
        logger.info(f"Starting transition image {transition_number} generation for breed: {breed}")
        
        # Convert image to base64
        if isinstance(original_image_data, bytes):
            image_base64 = base64.b64encode(original_image_data).decode('utf-8')
        else:
            image_base64 = base64.b64encode(original_image_data.read()).decode('utf-8')
        
        logger.info(f"Image converted to base64, length: {len(image_base64)}")
        
        # Create prompt based on transition number
        if transition_number == 1:
            prompt = f"A photorealistic image showing a gradual transformation from a human face to a {breed} dog. This is the first transition - the face should show early signs of transformation: slightly more canine features, but still mostly human. The transformation should be subtle and natural-looking."
        elif transition_number == 2:
            prompt = f"A photorealistic image showing a gradual transformation from a human face to a {breed} dog. This is the second transition - the face should show more pronounced canine features: more dog-like snout, ears, and fur, but still retaining some human characteristics. The transformation should be natural and seamless."
        else:
            prompt = f"A photorealistic image showing a gradual transformation from a human face to a {breed} dog. This is transition {transition_number} of {total_transitions}."
        
        logger.info(f"Prompt created for transition {transition_number}, calling DALL-E")
        
        # Get OpenAI client
        client = get_client()
        
        # Use DALL-E to generate the image
        logger.info(f"Calling DALL-E API for transition {transition_number}")
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        logger.info(f"DALL-E API call completed for transition {transition_number}")
        
        # Download the generated image
        image_url = response.data[0].url
        logger.info(f"Image URL received: {image_url[:50]}...")
        
        import requests
        logger.info(f"Downloading image from URL for transition {transition_number}")
        img_response = requests.get(image_url, timeout=60)
        img_response.raise_for_status()
        
        logger.info(f"Image downloaded successfully for transition {transition_number}, size: {len(img_response.content)} bytes")
        return img_response.content
        
    except Exception as e:
        logger.error(f"Error generating transition image {transition_number}: {type(e).__name__}: {str(e)}", exc_info=True)
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
        logger.info(f"Starting final dog image generation for breed: {breed}")
        
        prompt = f"A photorealistic portrait of a {breed} dog that closely resembles the facial features and expression of the human in the reference image. The dog should have the same general facial structure, eye shape, and expression as the human, but fully transformed into a {breed}. High quality, detailed, professional photography style."
        
        logger.info("Prompt created for final image, calling DALL-E")
        
        # Get OpenAI client
        client = get_client()
        
        # Use DALL-E to generate the final image
        logger.info("Calling DALL-E API for final image")
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        logger.info("DALL-E API call completed for final image")
        
        # Download the generated image
        image_url = response.data[0].url
        logger.info(f"Image URL received: {image_url[:50]}...")
        
        import requests
        logger.info("Downloading final image from URL")
        img_response = requests.get(image_url, timeout=60)
        img_response.raise_for_status()
        
        logger.info(f"Final image downloaded successfully, size: {len(img_response.content)} bytes")
        return img_response.content
        
    except Exception as e:
        logger.error(f"Error generating final dog image: {type(e).__name__}: {str(e)}", exc_info=True)
        return None
