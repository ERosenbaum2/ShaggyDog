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
                    "content": "You are a visual pattern matching expert for creative art projects. You analyze images to identify visual characteristics like shapes, colors, textures, and proportions, then match these to dog breeds based on similar visual patterns. You focus purely on observable visual features without identifying subjects."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analyze this image as a collection of visual patterns and characteristics. Identify the following VISUAL FEATURES (treat this as abstract visual analysis, not subject identification):

VISUAL CHARACTERISTICS TO IDENTIFY:
1. Face shape pattern: (round, oval, square, long, heart-shaped, angular, rectangular)
2. Eye pattern: (shape - almond/round/oval, size relative to face, spacing - wide/close, positioning)
3. Color palette: (dominant colors, tones - light/medium/dark, color distribution, contrast levels)
4. Texture patterns: (if visible - smooth, textured, curly patterns, straight lines, wavy patterns)
5. Structural shapes: (cheekbone angles, jawline shape - square/round/angular, nose proportions)
6. Body proportions: (if visible - overall frame size, head-to-body ratio, build pattern - compact/elongated/stocky)
7. Visual energy: (conveyed through expression - bright/calm/intense/playful based on visual cues)
8. Geometric patterns: (facial feature arrangement, symmetry, proportional relationships)

Based on these VISUAL PATTERNS you observe, match them to a dog breed with similar visual characteristics:

MATCHING CRITERIA:
- Facial structure patterns (which breed has similar geometric face shape?)
- Color palette matching (which breed's coat colors match the dominant colors in the image?)
- Texture similarities (which breed's fur texture matches visible texture patterns?)
- Proportional patterns (which breed has similar head-to-body proportions?)
- Structural similarities (which breed has similar bone structure patterns?)

This is a creative visual art matching task. Analyze the image purely as visual patterns, shapes, and colors.

Respond in EXACTLY this format:
BREED: [specific dog breed name]
REASONING: [2-3 sentences describing the visual patterns, shapes, colors, and structural characteristics you observed that match this breed's appearance]

Example:
BREED: Rottweiler
REASONING: The image shows a square, angular facial structure pattern with strong geometric lines, matching a Rottweiler's head shape. The dominant dark color palette with tan accents aligns with the Rottweiler's black and tan coat pattern. The structural proportions show a stocky, powerful build pattern similar to this breed's characteristic physique."""
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
