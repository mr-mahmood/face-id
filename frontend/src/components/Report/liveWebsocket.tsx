"use client";

import { API_BASE_URL } from "@/config/index";
import { Gate } from "@/src/types/gate";
import { useRouter } from 'next/navigation';
import { useActiveUser } from "@/src/contexts/active_user_context";
import { Area } from "@/src/types/area";
import { useState, useEffect, useRef, useCallback } from "react";
import { AccessHistory } from "@/src/types/accessHistory";

export default function GateReport() {
    const router = useRouter();
    const [hasError, setHasError] = useState(false);
    const [errorMessage, setErrorMessage] = useState('');
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

    // Track gates that are currently connecting to prevent duplicate connections
    const connectingGatesRef = useRef<Set<number>>(new Set());

    // Store carousel instances
    const carouselInstancesRef = useRef<Map<number, any>>(new Map());

    // Maximum number of events to keep per gate
    const MAX_EVENTS_PER_GATE = 50;

    const handleGateClick = useCallback((gateId: number) => {
        console.log(`Gate ID: ${gateId}`);
        const gate = gatesWithArea.find(item => item.gate.id === gateId);
        if (gate) {
            setSelectedGate(gate);
        }
    }, [gatesWithArea]);

    // Function to safely close a WebSocket connection
    const closeWebSocket = useCallback((gateId: number) => {
        const socket = webSocketsRef.current.get(gateId);
        if (socket) {
            socket.onopen = null;
            socket.onclose = null;
            socket.onerror = null;
            socket.onmessage = null;

            if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
                socket.close(1000, "Normal closure");
            }

            webSocketsRef.current.delete(gateId);
            connectingGatesRef.current.delete(gateId);
            console.log(`WebSocket cleaned up for gate ${gateId}`);
        }
    }, []);

    // Connect to WebSocket for selected gate
    useEffect(() => {
        if (!selectedGate) return;

        const gateId = selectedGate.gate.id;

        if (webSocketsRef.current.has(gateId) || connectingGatesRef.current.has(gateId)) {
            const existingSocket = webSocketsRef.current.get(gateId);
            if (existingSocket?.readyState === WebSocket.OPEN) {
                console.log(`WebSocket already connected for gate ${gateId}`);
                return;
            }
        }

        connectingGatesRef.current.add(gateId);
        console.log(`Creating WebSocket connection for gate ${gateId}`);
        
        const socket = new WebSocket(`ws://localhost:8000/ws/access-events/${gateId}/`);

        socket.onopen = () => {
            console.log(`✅ WebSocket connected for gate ${gateId}`);
            setHasError(false);
            connectingGatesRef.current.delete(gateId);
            webSocketsRef.current.set(gateId, socket);
        };

        socket.onclose = (event) => {
            console.log(`🔴 WebSocket disconnected for gate ${gateId}`, {
                code: event.code,
                reason: event.reason,
                wasClean: event.wasClean
            });
            webSocketsRef.current.delete(gateId);
            connectingGatesRef.current.delete(gateId);

            switch(event.code) {
                case 4000:
                    setHasError(true);
                    setErrorMessage('نیاز به احراز هویت مجدد');
                    router.prefetch('/login');
                    fetch(`${API_BASE_URL}/api/auth/logout/`, {
                        method: 'POST',
                        headers: { "Content-Type": "application/json" },
                        credentials: 'include',
                    }).catch(error => {
                        console.error("Error during logout fetch:", error instanceof Error ? error.message : String(error));
                    }).finally(() => {
                        setTimeout(() => {
                            router.push('/login');
                        }, 3000);
                    });
                    break;
                case 4001:
                    setHasError(true);
                    setErrorMessage('در ارتباط با گیت مدنظر شما مشکلی وجود دارد');
                    break;
                case 4002:
                    setHasError(true);
                    setErrorMessage('گیت مدنظر یافت نشد یا غیرفعال است');
                    break;
                case 4003:
                    setHasError(true);
                    setErrorMessage('شما اجازه این کار را ندارید');
                    break;
                default:
                    break;
            }
        };

        socket.onerror = (err) => {
            console.error(`❌ WebSocket error for gate ${gateId}:`, err);
            connectingGatesRef.current.delete(gateId);
        };

        socket.onmessage = (event) => {
            try {
                const data: AccessHistory = JSON.parse(event.data);
                console.log(data);

                setGateEvents(prev => {
                    const newMap = new Map(prev);
                    const currentEvents = newMap.get(gateId) || [];

                    const eventExists = currentEvents.some(
                        existingEvent => existingEvent.id === data.id
                    );

                    if (!eventExists) {
                        const updatedEvents = [data, ...currentEvents].slice(0, MAX_EVENTS_PER_GATE);
                        newMap.set(gateId, updatedEvents);
                        console.log(`📨 New event for gate ${gateId}:`, data.id);
                    } else {
                        console.log(`🔄 Duplicate event ignored for gate ${gateId}:`, data.id);
                    }

                    return newMap;
                });
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };

        return () => {
            closeWebSocket(gateId);
        };
    }, [selectedGate?.gate.id, closeWebSocket, router]);

    // Get events for current gate
    const currentGateEvents = selectedGate ? gateEvents.get(selectedGate.gate.id) || [] : [];

    // Initialize Bootstrap carousels without auto-slide
    useEffect(() => {
        if (!currentGateEvents.length) return;

        currentGateEvents.forEach((event) => {
            if (event.images && event.images.length > 1) {
                const carouselElement = document.querySelector(`#carousel-${event.id}`);
                if (carouselElement && !carouselInstancesRef.current.has(event.id)) {
                    const bsCarousel = new (window as any).bootstrap.Carousel(carouselElement, {
                        interval: false,
                        ride: false,
                        wrap: true
                    });
                    carouselInstancesRef.current.set(event.id, bsCarousel);

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
            console.log('Cleaning up all WebSocket connections');
            const gateIds = Array.from(webSocketsRef.current.keys());
            gateIds.forEach(gateId => {
                closeWebSocket(gateId);
            });
            webSocketsRef.current.clear();
            connectingGatesRef.current.clear();

            carouselInstancesRef.current.forEach((instance) => {
                if (instance && typeof instance.dispose === 'function') {
                    instance.dispose();
                }
            });
            carouselInstancesRef.current.clear();
        };
    }, [closeWebSocket]);

    // Helper function to format Persian date
    const formatPersianDate = (timestamp: string) => {
        try {
            const date = new Date(timestamp);
            return date.toLocaleTimeString('fa-IR') + ' ' + date.toLocaleDateString('fa-IR');
        } catch {
            return 'تاریخ نامعتبر';
        }
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
                                {gatesWithArea.map(({ gate, area }) => {
                                    if (gate.is_active && area.is_active) {
                                        return (
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
                                        );
                                    }
                                    return null;
                                })}
                                
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
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Right Content Area - Scrollable Events */}
            <div className="col-md-9 cards-scrollable" style={{ height: '86vh' }}>
                {currentGateEvents.length === 0 ? (
                    <>
                        {hasError && (
                            <div className="row">
                                <div className="col-md-6 col-xxl-4"></div>
                                <div className="col-md-6 col-xxl-4">
                                    <div className="card overflow-hidden b-s-6-danger">
                                        <div className="card-body">
                                            <i className="ti ti-alert-circle f-s-60 text-danger" style={{display: 'block', textAlign: 'center'}}></i>
                                            <h4 className="text-danger text-center">مشکلی به وجود آمد</h4>
                                            <p className="text-muted mb-0 text-center">{errorMessage}</p>
                                            {errorMessage.includes('احراز هویت') && (
                                                <div className="mt-1 text-center">
                                                    <span className="text-muted small">در حال انتقال به صفحه ورود</span>
                                                    <div className="spinner-border spinner-border-sm text-muted me-2" role="status">
                                                        <span className="visually-hidden">در حال انتقال</span>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                        <img alt="توضیحات تصویر" className="card-img-bottom mt-0" src="/images/background/error.jpg" />
                                    </div>
                                </div>
                                <div className="col-md-6 col-xxl-4"></div>
                            </div>
                        )}
                    </>
                ) : (
                    <div className="row">
                        {currentGateEvents.map((event) => {
                            const currentImageIndex = activeImageIndices.get(event.id) || 0;

                            return (
                                <div className="col-md-4 mb-0" key={event.id}>
                                    <div className={`card book-mark-card hover-effect b-r-25 ${event.status === 'ALLOWED' ? 'b-s-6-success' : 'b-s-6-danger'}`}>
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
                                                {/* Single row item */}
                                                <div className="row" style={{ width: '100% ' }}>
                                                    {event.status === 'ALLOWED' ? (
                                                        <span className="badge float-end text-light-success b-r-25 f-w-500 f-s-16 mt-0 mb-1">دسترسی مجاز</span>
                                                    ) : (
                                                        <span className="badge float-end text-light-danger b-r-25 f-w-500 f-s-16 mt-0 mb-1">دسترسی غیر مجاز</span>
                                                    )}
                                                </div>

                                                {/* Row 1: Name */}
                                                <div className="about-list-item" style={{ borderTop: '1px solid #dee2e6', paddingTop: '0.5rem' }}>
                                                    <span className="about-list-label f-s-15">مالک:</span>
                                                    <span className="about-list-value">
                                                        {event.user?.first_name || event.user?.last_name 
                                                            ? `${event.user?.first_name || ''} ${event.user?.last_name || ''}`.trim()
                                                            : '---'
                                                        }
                                                    </span>
                                                </div>

                                                {/* Row 2: Area and Gate*/}
                                                <div className="about-list-item">
                                                    <span className="about-list-label">محوطه:</span>
                                                    <span className="about-list-value">
                                                        {event.area?.name || event.gate?.name 
                                                            ? `${event.area?.name  || ''} ( ${event.gate?.name} )`.trim()
                                                            : '---'
                                                        }
                                                    </span>
                                                </div>

                                                {/* Row 3: Date and Confidence */}
                                                <div className="about-list-item">
                                                    <span className="about-list-label">تاریخ:</span>
                                                    <span className="about-list-value">
                                                        {formatPersianDate(event.timestamp)}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}