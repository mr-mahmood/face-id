
import { useRef, useEffect, useState } from "react";
import useWebcamUtils from "@/src/utils/webcam";
import { UserData } from "@/src/types/userData";
import { base64ToFormData } from "../../utils/base64ToFormData";
import { robustFetch } from "@/src/utils/apiFetch";
import { useRouter } from "next/navigation";

interface refrenceImagesProps {
    userData: UserData | null;
    setUserData: React.Dispatch<React.SetStateAction<UserData | null>>;
}

const RefrenceImagesModal: React.FC<refrenceImagesProps> = ({ userData, setUserData }) => {
    const router = useRouter();
    const { videoRef, startStream, captureFrame, stopStream } = useWebcamUtils();
    const [isStart, setIsStart] = useState<boolean>(false);
    const [capturedImage, setCapturedImage] = useState<string | null>(null);
    const [isSubmiting, setIsSubmiting] = useState<boolean>(false);
    const [uploadError, setUploadError] = useState<string | null>(null);

    const modalRef = useRef<HTMLDivElement>(null);
    const closeBtnRef = useRef<HTMLButtonElement>(null);

    useEffect(() => {
        if (userData) {
            const modalElement = modalRef.current;

            const handleShow = () => {
                startStream().catch(err => console.error("Failed to start stream:", err));
            };
            const handleHide = () => {
                setCapturedImage(null);
                setUploadError(null);
                stopStream();
            };
            modalElement?.addEventListener("show.bs.modal", handleShow);
            modalElement?.addEventListener("hide.bs.modal", handleHide);
            return () => {
                modalElement?.removeEventListener("show.bs.modal", handleShow);
                modalElement?.removeEventListener("hide.bs.modal", handleHide);
            };
        }
    }, [userData]);

    useEffect(() => {
        if (!capturedImage && isStart) {
            startStream().catch(err => console.error("Failed to start stream:", err));
            setIsStart(false);
        }
    }, [capturedImage]);

    const handleUpload = async () => {
        const imageDataUrl = captureFrame();
        if (!imageDataUrl) console.warn("Failed to capture frame: no active stream or video element");
        if (!imageDataUrl || !userData) return;
        setIsSubmiting(true);

        const formData = base64ToFormData(imageDataUrl, 'image');
        try {
            const response = await robustFetch({
                url: `api/refrence-images/${userData.id}/`,
                method: 'POST',
                headers: {},
                body: formData,
                router,
            });
            if (!response.success) {
                throw new Error(response.message || "Upload failed");
            }
            const newImage = response.data.reference;
            setUserData(prev => {
                if (!prev) return null;
                const updatedImages = [...(prev.reference_images || []), newImage];
                return {
                    ...prev,
                    reference_images: updatedImages
                };
            });
        } catch (error) {
            console.error("Error uploading reference image:", error);
            throw error;
        } finally {
            setUploadError(null);
            setIsSubmiting(false)
        }
    };

    return (
        <div className="modal fade" id="referenceImage" tabIndex={-1} aria-labelledby="referenceImageLabel" aria-hidden="true" ref={modalRef}>
            <div className="modal-dialog modal-dialog-centered">
                <div className="modal-content">
                    <div className="modal-header">
                        <h5 className="modal-title" id="referenceImageLabel">افزودن عکس جدید</h5>
                    </div>
                    <div className="modal-body">
                        <div className="image-preview-container">
                            <video
                                key="webcam-video"
                                ref={videoRef}
                                autoPlay
                                playsInline
                                muted
                                style={{
                                    width: '100%',
                                    height: '100%',
                                    objectFit: 'cover'
                                }}
                            />
                        </div>
                        <div className="mt-3 text-center">
                            <button
                                className="btn btn-light-danger b-r-25 f-s-17"
                                data-bs-dismiss="modal"
                                type="button"
                                ref={closeBtnRef}
                            >
                                انصراف
                            </button>
                            <button
                                className="btn btn-light-see-blue b-r-25 f-s-17"
                                onClick={handleUpload}
                                disabled={isSubmiting}
                            >
                                گرفتن عکس
                            </button>
                            <div className="text-center">
                                {uploadError && <p className="mt-2 mb-0 text-danger f-s-20">{uploadError}</p>}
                            </div>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
};
export default RefrenceImagesModal;
