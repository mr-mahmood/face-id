import { useEffect, useState } from "react";
import { UserData } from "@/src/types/userData";
import { useRouter } from 'next/navigation';
import { ReferenceImage } from "@/src/types/referenceImage";
import { robustFetch } from "@/src/utils/apiFetch";
import UserInfoCard from '@/src/components/common/UserInfoCard';

interface UserRefrenceImagesProps {
    UserData: UserData | null;
}

const UserRefrenceImages: React.FC<UserRefrenceImagesProps> = ({ UserData }) => {

    const router = useRouter();
    const [referenceImages, setReferenceImages] = useState<Array<ReferenceImage>>([]);

    useEffect(() => {
        if (UserData) {
            setReferenceImages([...UserData.reference_images].reverse())
        }
    }, [UserData]);

    const handleDelete = async (user_id: string, image_id: string) => {
        if (!user_id || !image_id) return;
        try {
            const response = await robustFetch({
                url: `api/refrence-images/user/${user_id}/image/${image_id}/`,
                method: 'DELETE',
                headers: {},
                body: null,
                router,
            });
            if (!response.success) {
                throw new Error(response.message || "delete failed");
            } else {
                setReferenceImages(prevImages =>
                    prevImages.filter(image => image.id !== image_id)
                );
            }
        } catch (error) {
            console.error("Error deleting reference image:", error);
            throw error;
        }
    };

    return (
        <>
            <div className="row">
                <div className="col-lg-3">
                    <UserInfoCard
                        height="62vh"
                        userData={UserData}
                    />
                </div>
                <div className="col-lg-9">
                    <div className="card hover-effect b-r-25">
                        <div className="card-header row">
                            <div className="col-md-9">
                                <h3>عکس های ثبت شده</h3>
                            </div>
                            <div className="col-md-3">
                                <button
                                    className="btn btn-light-see-blue b-r-25 f-s-20 f-w-500"
                                    data-bs-target="#referenceImage"
                                    data-bs-toggle="modal"
                                >
                                    ثبت عکس جدید
                                </button>
                            </div>
                        </div>
                        <div className="card-body" style={{ height: '60vh' }}>
                            <div className="cards-scrollable">
                                <div className="row">
                                    {UserData && referenceImages ? (
                                        referenceImages.map((img) => (
                                            <div className="col-4 col-sm-4 col-lg-4" key={img.id}>
                                                <div className="custome-wrapper-2">
                                                    <img alt="عکس مرجع" src={img.image} />
                                                    <div className="custome-wrapper-2-content">
                                                        <h5>حذف این عکس</h5>
                                                        <button
                                                            className="btn btn-light-danger icon-btn b-r-10 delete-btn f-s-25"
                                                            type="button"
                                                            onClick={() => handleDelete(UserData.id, img.id)}
                                                        >
                                                            <i className="ti ti-trash"></i>
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        ))
                                    ) : (
                                        <></>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}

export default UserRefrenceImages;