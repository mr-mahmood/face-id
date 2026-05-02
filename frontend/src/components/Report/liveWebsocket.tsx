"use client";

import { Gate } from "@/src/types/gate";
import { useActiveUser } from "@/src/contexts/active_user_context";
import { Area } from "@/src/types/area";
import { useState, useEffect, useRef } from "react";
import { AccessHistory } from "@/src/types/accessHistory";

export default function GateReport() {
    const { activeUser } = useActiveUser();
    // Store active image index for each event separately
    const [activeImageIndices, setActiveImageIndices] = useState<Map<number, number>>(new Map());
    // Flatten all gates from all areas with area context
    const gatesWithArea: { gate: Gate; area: Area }[] = activeUser?.areas?.flatMap(area =>
        area.gates.map(gate => ({ gate, area }))
    ) || [];

    const [selectedGate, setSelectedGate] = useState<{ gate: Gate; area: Area } | null>(
        gatesWithArea.length > 0 ? gatesWithArea[0] : null
    );

    // State to store events for each gate
    const [gateEvents, setGateEvents] = useState<Map<number, AccessHistory[]>>(new Map());

    // WebSocket connections ref
    const webSocketsRef = useRef<Map<number, WebSocket>>(new Map());

    // Store carousel instances
    const carouselInstancesRef = useRef<Map<number, any>>(new Map());

    const handleGateClick = (gateId: number) => {
        console.log(`Gate ID: ${gateId}`);
        const gate = gatesWithArea.find(item => item.gate.id === gateId);
        if (gate) {
            setSelectedGate(gate);
        }
    };

    // Connect to WebSocket for selected gate
    useEffect(() => {
        if (!selectedGate) return;

        const gateId = selectedGate.gate.id;

        // Check if already connected
        if (webSocketsRef.current.has(gateId)) {
            return;
        }

        // Create WebSocket connection
        const socket = new WebSocket(`ws://localhost:8000/ws/access-events/${gateId}/`);

        socket.onopen = () => {
            console.log(`WebSocket connected for gate ${gateId}`);
        };

        socket.onclose = () => {
            console.log(`WebSocket disconnected for gate ${gateId}`);
            webSocketsRef.current.delete(gateId);
        };

        socket.onerror = (err) => {
            console.error(`WebSocket error for gate ${gateId}:`, err);
        };

        socket.onmessage = (event) => {
            const data: AccessHistory = JSON.parse(event.data);
            console.log(`Event received for gate ${gateId}:`, data);

            // Update events for this gate
            setGateEvents(prev => {
                const newMap = new Map(prev);
                const currentEvents = newMap.get(gateId) || [];
                // Add new event to the beginning of the array
                newMap.set(gateId, [data, ...currentEvents]);
                return newMap;
            });
        };

        // Store the socket
        webSocketsRef.current.set(gateId, socket);

        // Cleanup on unmount or gate change
        return () => {
            if (socket.readyState === WebSocket.OPEN) {
                socket.close();
            }
            webSocketsRef.current.delete(gateId);
        };
    }, [selectedGate]);

    // Get events for current gate - MOVED THIS UP before the carousel useEffect
    const currentGateEvents = selectedGate ? gateEvents.get(selectedGate.gate.id) || [] : [];

    // Initialize Bootstrap carousels without auto-slide - MOVED THIS AFTER currentGateEvents declaration
    useEffect(() => {
        if (!currentGateEvents.length) return;

        // Initialize each carousel
        currentGateEvents.forEach((event) => {
            if (event.images && event.images.length > 1) {
                const carouselElement = document.querySelector(`#carousel-${event.id}`);
                if (carouselElement && !carouselInstancesRef.current.has(event.id)) {
                    // Initialize carousel with interval: false to prevent auto-slide
                    const bsCarousel = new (window as any).bootstrap.Carousel(carouselElement, {
                        interval: false,
                        ride: false,
                        wrap: true
                    });
                    carouselInstancesRef.current.set(event.id, bsCarousel);

                    // Listen to slide events to update state
                    carouselElement.addEventListener('slid.bs.carousel', (e: any) => {
                        setActiveImageIndices(prev => {
                            const newMap = new Map(prev);
                            newMap.set(event.id, e.to);
                            return newMap;
                        });
                    });
                }
            }
        });

        // Cleanup
        return () => {
            carouselInstancesRef.current.forEach((instance, id) => {
                instance.dispose();
                carouselInstancesRef.current.delete(id);
            });
        };
    }, [currentGateEvents]);

    // Cleanup all WebSockets on component unmount
    useEffect(() => {
        return () => {
            webSocketsRef.current.forEach((socket) => {
                if (socket.readyState === WebSocket.OPEN) {
                    socket.close();
                }
            });
            webSocketsRef.current.clear();

            // Cleanup carousels
            carouselInstancesRef.current.forEach((instance) => {
                instance.dispose();
            });
            carouselInstancesRef.current.clear();
        };
    }, []);

    // Helper function to format Persian date
    const formatPersianDate = (timestamp: string) => {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('fa-IR') + ' ' + date.toLocaleDateString('fa-IR');
    };

    const { getRoleInFarsi } = useActiveUser();

    const getRoleBadgeClass = (role: string) => {
        switch (role) {
            case "مدیر ارشد":
                return "text-light-cyan";
            case "مدیر":
                return "text-light-see-blue";
            case "ادمین":
                return "text-light-info";
            case "کارمند":
                return "text-light-purple";
            default:
                return "text-light-primary";
        }
    };

    return (
        <div className="row">

            <div className="col-md-3">
                <div className="card hover-effect b-r-25 cards-scrollable" style={{ height: '41vh' }}>
                    <div className="card-header">
                        <h5>گیت ها (محوطه)</h5>
                    </div>
                    <div className="card-body">
                        <div className="vertical-tab setting-tab">
                            <ul className="nav nav-tabs tab-light-info m-0 flex-column" id="v-bg" role="tablist">
                                {gatesWithArea.map(({ gate, area }, index) => (
                                    <li className="nav-item w-100 mb-2" key={gate.id} role="presentation">
                                        <button
                                            aria-controls={`tab-${gate.id}`}
                                            aria-selected={selectedGate?.gate.id === gate.id}
                                            className={`nav-link b-r-25 w-100 text-start ${selectedGate?.gate.id === gate.id ? 'active' : ''}`}
                                            data-bs-target={`#tab-${gate.id}-pane`}
                                            data-bs-toggle="tab"
                                            id={`tab-${gate.id}`}
                                            role="tab"
                                            type="button"
                                            onClick={() => handleGateClick(gate.id)}
                                        >
                                            <i className="ph-bold ph-door pe-2"></i>
                                            {gate.name} ({area.name})
                                        </button>
                                    </li>
                                ))}

                                {gatesWithArea.length === 0 && (
                                    <li className="nav-item">
                                        <div className="alert alert-info m-3">
                                            هیچ گیت دسترسی برای شما تعریف نشده است
                                        </div>
                                    </li>
                                )}
                            </ul>
                        </div>
                    </div>
                </div>

                {/* Gate Information Card */}
                {selectedGate && (
                    <div className="card hover-effect mt-3 b-r-25 cards-scrollable" style={{ height: '40vh' }}>
                        <div className="card-header">
                            <h5>اطلاعات گیت</h5>
                        </div>
                        <div className="card-body ">
                            <div className="about-list">
                                <div className="about-list-item">
                                    <span className="about-list-label">
                                        <i className="ti ti-id"></i> شناسه:
                                    </span>
                                    <span className="about-list-value">
                                        {selectedGate.gate.id}
                                    </span>
                                </div>
                                <div className="about-list-item">
                                    <span className="about-list-label">
                                        <i className="ti ti-building"></i> محوطه:
                                    </span>
                                    <span className="about-list-value">
                                        {selectedGate.area.name}
                                    </span>
                                </div>
                                <div className="about-list-item">
                                    <span className="about-list-label">
                                        <i className="ti ti-door"></i> گیت:
                                    </span>
                                    <span className="about-list-value">
                                        {selectedGate.gate.name}
                                    </span>
                                </div>
                                <div className="about-list-item">
                                    <span className="about-list-label">
                                        <i className="ti ti-camera"></i> دوربین:
                                    </span>
                                    <span className="about-list-value">
                                        {selectedGate.gate.camera || 'ندارد'}
                                    </span>
                                </div>
                                <div className="about-list-item">
                                    <span className="about-list-label">
                                        <i className="ti ti-circle-check"></i> نقش:
                                    </span>
                                    <div style={{ justifySelf: "end" }}>
                                        {(() => {
                                            if (selectedGate.gate.role === "ENTERY") {
                                                return (
                                                    <span className="badge text-light-cyan b-r-25 f-s-17">
                                                        <i className="ti ti-door-enter"></i> ورودی
                                                    </span>
                                                );
                                            } else if (selectedGate.gate.role === "EXIT") {
                                                return (
                                                    <span className="badge text-light-dark-orange b-r-25 f-s-17">
                                                        <i className="ti ti-door-exit"></i> خروجی
                                                    </span>
                                                );
                                            } else if (selectedGate.gate.role === "SURVEILLANCE") {
                                                return (
                                                    <span className="badge text-light-see-blue b-r-25 f-s-17">
                                                        <i className="ti ti-device-computer-camera"></i> نظارت
                                                    </span>
                                                );
                                            }
                                        })()}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Right Content Area - Scrollable Events */}
            <div className="col-md-9 cards-scrollable" style={{ height: '86vh' }}>

                <div className="row">
                    {currentGateEvents.map((event) => {
                        const currentImageIndex = activeImageIndices.get(event.id) || 0;

                        return (
                            <div className="col-md-4 mb-0" key={event.id}>
                                <div className={`card book-mark-card hover-effect b-r-25 ${event.status === 'ALLOWED' ? 'b-s-4-success' : 'b-s-4-danger'}`}>
                                    <div className="card-body">
                                        {event.images && event.images.length > 0 && (
                                            <>
                                                <div
                                                    id={`carousel-${event.id}`}
                                                    className="carousel slide"
                                                >
                                                    <div className="carousel-inner">
                                                        {event.images.map((image, idx) => (
                                                            <div
                                                                key={image.id}
                                                                className={`carousel-item ${idx === currentImageIndex ? 'active' : ''}`}
                                                            >
                                                                <img
                                                                    alt={`تصویر ${idx + 1} از گزارش دسترسی`}
                                                                    className="w-100 d-block b-r-25"
                                                                    src={image.image}
                                                                />
                                                            </div>
                                                        ))}
                                                    </div>
                                                    {event.images.length > 1 && (
                                                        <>
                                                            <button
                                                                className="carousel-control-prev"
                                                                data-bs-slide="prev"
                                                                data-bs-target={`#carousel-${event.id}`}
                                                                type="button"
                                                            >
                                                                <span aria-hidden="true" className="carousel-control-prev-icon"></span>
                                                                <span className="visually-hidden">قبل</span>
                                                            </button>
                                                            <button
                                                                className="carousel-control-next"
                                                                data-bs-slide="next"
                                                                data-bs-target={`#carousel-${event.id}`}
                                                                type="button"
                                                            >
                                                                <span aria-hidden="true" className="carousel-control-next-icon"></span>
                                                                <span className="visually-hidden">بعد</span>
                                                            </button>
                                                        </>
                                                    )}
                                                </div>
                                                {/* Image counter */}
                                                {event.images.length > 1 && (
                                                    <div className="text-center mt-2">
                                                        <small className="text-muted">
                                                            {currentImageIndex + 1} از {event.images.length}
                                                        </small>
                                                    </div>
                                                )}
                                            </>
                                        )}
                                        <div className="about-list">
                                            <div className="about-list-item">
                                                <span className="about-list-label">
                                                    دسترسی:
                                                </span>
                                                <span className="about-list-value">
                                                    {event.status === 'ALLOWED' ? (
                                                        <span className="badge float-end text-light-success b-r-25 f-w-500 f-s-16 mt-0 mb-1">مجاز</span>
                                                    ) : (
                                                        <span className="badge float-end text-light-danger b-r-25 f-w-500 f-s-16 mt-0 mb-1">غیر مجاز</span>
                                                    )}
                                                </span>
                                            </div>
                                            <div className="about-list-item">
                                                <span className="about-list-label">
                                                    نام:
                                                </span>
                                                <span className="about-list-value">
                                                    {event.user && event.user.first_name ? (
                                                        <>
                                                            {`${event.user.first_name} ${event.user.last_name}`}
                                                        </>
                                                    ) : (
                                                        `---`
                                                    )}
                                                </span>
                                            </div>
                                            <div className="about-list-item">
                                                <span className="about-list-label">
                                                    کد پرسنلی:
                                                </span>
                                                <span className="about-list-value">
                                                    {event.user && event.user.employe_number ? (
                                                        `${event.user.employe_number}`
                                                    ) : (
                                                        `---`
                                                    )}
                                                </span>
                                            </div>
                                            <div className="about-list-item">
                                                <span className="about-list-label">
                                                    تاریخ:
                                                </span>
                                                <span className="about-list-value">
                                                    {formatPersianDate(event.timestamp)}
                                                </span>
                                            </div>
                                            <div className="about-list-item">
                                                <span className="about-list-label">
                                                    اطمینان:
                                                </span>
                                                <span className="about-list-value">
                                                    {event.confidence ? (
                                                        `% ${Math.round(event.confidence * 100)}`
                                                    ) : (
                                                        `---`
                                                    )}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}