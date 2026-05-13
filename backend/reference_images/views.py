from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from reference_images.models import ReferenceImages
from authentication.permissions import IsSuperOrManager
from reference_images.serializers import ReferenceImagesSerializer
from users.models import User
from core.exceptions import APIError, RefImageError
from cv_engine.pipeline_loader import load_pipeline
from cv_engine.faiss import build_global_faiss, faiss_save
# from cv.tasks import faiss_update_task
import numpy as np
import cv2
from reference_images.models import ReferenceImages
from typing import cast
    
class ReferenceImageEnrollAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsSuperOrManager]
    serializer_class = ReferenceImagesSerializer
    
    def post(self, request, user_id):
        current_user: User = request.user
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        image_file = validated_data.get('image')  # type: ignore
        user = User.get_user(user_id=user_id, current_user=current_user)
        
        if not image_file:
            raise APIError(RefImageError.INVALID_IMAGE)
    
        enroll_pipeline = load_pipeline()
        try:
            image = cv2.imdecode(
                np.frombuffer(image_file.read(), np.uint8),
                cv2.IMREAD_COLOR
            )
            
            if image is None:
                raise APIError(RefImageError.INVALID_IMAGE)

            result = enroll_pipeline.process_single_image(image)
            if result == None:
                raise APIError(RefImageError.INVALID_IMAGE)
            
            # --- Save for the employe user ---
            ref = ReferenceImages(user=user)
            ref.image = image_file
            ref.set_embedding(result["embedding"])
            ref.save()
            
            build_global_faiss()
            faiss_save()

            
            # faiss_update_task.delay()
            return Response({
                "message": f"reference image processed for user {user.id}",
                "reference": ReferenceImagesSerializer(ref, context={"request": request}).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            raise APIError(RefImageError.INVALID_IMAGE)                 


class ReferenceImageDeleteAPIView(APIView):
    permission_classes = [IsSuperOrManager]

    def delete(self, request, user_id, image_id):
        try:
            ref = ReferenceImages.objects.get(id=image_id, user_id=user_id)
        except ReferenceImages.DoesNotExist:
            raise APIError(RefImageError.IMAGE_NOT_EXIST)
        
        if ref.image:
            ref.image.delete(save=False)
        ref.delete()
        
        build_global_faiss()
        faiss_save()
        
        # faiss_remove_task.delay(image_id) # Uncomment when ready
        
        return Response({
            "message": "Reference image deleted successfully.",
        }, status=status.HTTP_200_OK)