# utils.py
import io
import numpy as np
from PIL import Image
from areas.models import Area
from users.models import User
from gates.models import Gate
from django.core.files.base import ContentFile
from user_permisions.models import AccessPolicy
from access_verification.models import AccessHistory, AccessHistoryImage


def get_gate(gate_id):
    """Get gate instance with proper error handling"""
    if not gate_id:
        return None
    
    try:
        return Gate.get_gate(gate_id)
    except Exception as e:
        return None


def process_images(images, target_size=(1920, 1080), quality=100):
    """Process uploaded images and prepare for face detection
    
    Args:
        images: List of uploaded image files
        target_size: Tuple of (width, height) for resizing
        quality: JPEG quality (1-100)
        enhance: Whether to enhance image quality
    """
    from PIL import Image
    np_images = []
    image_files_data = []
    
    for idx, image_file in enumerate(images):
        try:
            # Read and process image
            image_bytes = image_file.read()
            
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                original_size = img.size
                
                # Resize with high-quality resampling
                resized_image = img.resize(target_size, Image.Resampling.LANCZOS)
                image_np = np.array(resized_image)
                np_images.append(image_np)
                
                # Save resized image with optimization
                resized_bytes = io.BytesIO()
                resized_image.save(
                    resized_bytes, 
                    format='JPEG', 
                    quality=quality, 
                    optimize=True,
                    progressive=True  # For faster web loading
                )
                
                unique_filename = f"capture_{idx+1}_{original_size[0]}x{original_size[1]}.jpg"
                image_files_data.append({
                    'file': ContentFile(resized_bytes.getvalue(), name=unique_filename),
                    'original_name': unique_filename,
                    'order': idx,
                })
            
            # Reset file pointer
            image_file.seek(0)
            
        except Exception as e:
            print(f"Error processing image {idx}: {e}")
            continue
    
    return np_images, image_files_data


def extract_embeddings(face_pipeline, np_images):
    """Extract face embeddings from processed images"""
    if not np_images:
        return []
    
    try:
        faces = face_pipeline.process_batch_image(np_images)
    except Exception as e:
        return []
    
    embeddings = []
    for face in faces:
        if face is not None and 'embedding' in face:
            embeddings.append(face['embedding'])
    
    return embeddings


def get_user_from_recognition(recognition_result):
    """Get user from recognition result"""
    if not recognition_result:
        return None
    
    if recognition_result.get('status') != 'known':
        return None
    
    label = recognition_result.get('label')
    if not label:
        return None
    
    try:
        return User.get_user_for_backend(label)
    except Exception as e:
        return None


def check_access_permission(user:User | None, gate:Gate | None, recognition_result):
    """Check if user has access permission"""
    
    # Case: No face detected or unknown face
    if not recognition_result or recognition_result.get('status') != 'known':
        return AccessHistory.Status.DENIED, "Access denied - face unknown or not recognized"
    
    # Case: Face recognized but user not found in system
    if not user:
        return AccessHistory.Status.DENIED, f"Access denied - User not found in database"
    
    # Case: user is inactive
    if not user.is_active:
        return AccessHistory.Status.DENIED, "Access denied - user is not active"
    
    # Case: No gate specified
    if not gate:
        return AccessHistory.Status.DENIED, "Access denied - no gate specified"
    
    # Case: Area is inactive
    if not gate.is_active:
        return AccessHistory.Status.DENIED, "Access denied - gate is not active"
    
    area: Area = gate.area
    # Case: Area is inactive
    if not area.is_active:
        return AccessHistory.Status.DENIED, "Access denied - area is not active"
    
    confidence = recognition_result.get('similarity', 0)
    # Case: Check area access permission
    try:
        has_access = AccessPolicy.has_access(user_id=user.id, area_id=area.id)
    except Exception as e:
        return AccessHistory.Status.DENIED, "Access denied - policy check failed"
    
    if has_access:
        return AccessHistory.Status.ALLOWED, f"Access granted - confidence: {confidence:.2f}"
    else:
        return AccessHistory.Status.DENIED, f"Access denied - user {user.id} does not have access to this area"


def create_access_history(user, gate, area, status, reason, confidence, image_files_data):
    """Create and save access history record with multiple images"""
    # Create the access history record first
    access_history = AccessHistory(
        user=user,
        gate=gate,
        area=area,
        status=status,
        reason=reason,
        confidence=confidence
    )
    
    # Save to get the ID for folder path
    access_history.save()
    
    # Save all images
    if image_files_data:
        for image_data in image_files_data:
            AccessHistoryImage.objects.create(
                access_history=access_history,
                image=image_data['file'],
                order=image_data['order']
            )
    
    return access_history