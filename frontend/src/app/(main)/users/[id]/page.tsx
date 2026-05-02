"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { robustFetch } from '@/src/utils/apiFetch';
import { UserData } from "@/src/types/userData";
import { LoadingSpinnerFullPage } from '@/src/components/common/LoadingSpinner';
import { useActiveUser } from "@/src/contexts/active_user_context";
import UserInformationForm from '@/src/components/User/UserInformationForm';
import ProfileImageUploader from '@/src/components/User/UserProfileImage';
import UserAreasList from '@/src/components/User/UserAreaAccess';
import WebcamModal from "@/src/components/common/WebcamModal";
import UserRefrenceImages from '@/src/components/User/UserRefrenceImagesList';
import RefrenceImagesModal from '@/src/components/User/UserRefrenceImagesModal';
import ErrorCard from "@/src/components/common/ErrorConnectToBackend";

export default function EditUserePage() {
    const router = useRouter();
    const { activeUser } = useActiveUser();
    const [user, setUser] = useState<UserData | null>(null);
    const [loading, setLoading] = useState(true);
    const [hasError, setHasError] = useState(false);
    const [errorPageCode, setErrorPageCode] = useState<number | undefined>(undefined);

    useEffect(() => {
        const pathParts = window.location.pathname.split('/');
        const id = pathParts[pathParts.length - 1];
        const fetchUser = async () => {
            try {
                const response = await robustFetch({
                    url: `api/users/${id}`,
                    method: 'GET',
                    headers: { "Content-Type": "application/json" },
                    body: null,
                    router: router
                });
                if (response.success !== true) {
                    setErrorPageCode(response.code);
                    setHasError(true);
                    throw new Error(`error while fetch user data${response.message}`);
                } else {
                    setUser(response.data.user);
                }
            } catch (err) {
                setHasError(true);
                console.error('error fetching user data', err);
            } finally {
                setLoading(false);
            }
        };
        fetchUser();
    }, []);

    const handleUserUpdated = (updatedUser: UserData) => {
        setUser(updatedUser);
    };

    return (
        <>
            <title>user Info</title>
            {loading ? (
                <LoadingSpinnerFullPage isLoading={loading} />
            ) : !hasError && user ? (
                <>
                    {activeUser && activeUser.role === "SUPER" ? (
                        <>
                            <div className="col-12">
                                <div className="card hover-effect b-r-25">
                                    <div className="card-body">
                                        <div className="nav custom-navstpes d-flex" id="justify-about-tab" role="tablist">
                                            <button
                                                aria-controls="personal-info-tab-pane"
                                                aria-selected="true"
                                                className="btn nav-link flex-grow-1 text-center active"
                                                data-bs-target="#personal-info-tab-pane"
                                                data-bs-toggle="tab"
                                                id="personal-info-tab"
                                                role="tab"
                                                type="button"
                                            >
                                                <span className="d-flex align-items-center">
                                                    <span><i className="ti ti-id-badge f-s-25"></i></span>
                                                    <span className="text-start ms-3 custom-title d-flex flex-column">
                                                        <span className="f-w-500 f-s-20 mb-1">اطلاعات شخصی</span>
                                                    </span>
                                                </span>
                                            </button>
                                            <button
                                                aria-controls="area-access-tab-pane"
                                                aria-selected="false"
                                                className="btn nav-link text-center flex-grow-1"
                                                data-bs-target="#area-access-tab-pane"
                                                data-bs-toggle="tab"
                                                id="area-access-tab"
                                                role="tab"
                                                type="button"
                                            >
                                                <span className="d-flex align-items-center">
                                                    <span><i className="ti ti-lock-access pe-2"></i></span>
                                                    <span className="text-start ms-3 custom-title d-flex flex-column">
                                                        <span className="f-w-500 f-s-20 mb-1">دسترسی محوطه ها</span>
                                                    </span>
                                                </span>
                                            </button>
                                            <button
                                                aria-controls="user-refrence-images-tab-pane"
                                                aria-selected="false"
                                                className="btn nav-link text-center flex-grow-1"
                                                data-bs-target="#user-refrence-images-tab-pane"
                                                data-bs-toggle="tab"
                                                id="user-refrence-images-tab"
                                                role="tab"
                                                type="button"
                                            >
                                                <span className="d-flex align-items-center">
                                                    <span><i className="ti ti-camera pe-2"></i></span>
                                                    <span className="text-start ms-3 custom-title d-flex flex-column">
                                                        <span className="f-w-500 f-s-20 mb-1">عکس های رفرنس</span>
                                                    </span>
                                                </span>
                                            </button>

                                        </div>
                                    </div>
                                </div>
                            </div>
                        </>
                    ) : (
                        <></>
                    )}
                    <div className="tab-content mt-3">
                        <div
                            className="tab-content mt-3"
                            id="justify-LightContent"
                        >
                            <div
                                aria-labelledby="personal-info-tab"
                                className="tab-pane fade show active"
                                id="personal-info-tab-pane"
                                role="tabpanel"
                                tabIndex={-1}
                            >
                                <div className="col-12">
                                    <div className="card hover-effect b-r-25">
                                        <div className="card-body">

                                            <ProfileImageUploader
                                                UserData={user}
                                            />

                                            <UserInformationForm
                                                UserData={user}
                                                setUserData={setUser}
                                                mode='edit'
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>
                            {activeUser && activeUser.role === "SUPER" ? (
                                <>
                                    <div
                                        aria-labelledby="area-access-tab"
                                        className="tab-pane fade"
                                        id="area-access-tab-pane"
                                        role="tabpanel"
                                        tabIndex={-1}
                                    >
                                        <UserAreasList
                                            UserData={user}
                                        />
                                    </div>
                                    <div
                                        aria-labelledby="user-refrence-images-tab"
                                        className="tab-pane fade"
                                        id="user-refrence-images-tab-pane"
                                        role="tabpanel"
                                        tabIndex={-1}
                                    >
                                        <UserRefrenceImages
                                            UserData={user}
                                        />
                                    </div>
                                </>
                            ) : (
                                <></>
                            )}
                        </div>
                    </div>
                    <WebcamModal
                        userData={user}
                        onUserUpdated={handleUserUpdated}
                    />
                    {activeUser && activeUser.role === "SUPER" ? (
                        <RefrenceImagesModal
                            userData={user}
                            setUserData={setUser}
                        />
                    ) : (
                        <></>
                    )}
                </>
            ) : (
                <ErrorCard
                    code={errorPageCode}
                />
            )}
        </>
    );


}
