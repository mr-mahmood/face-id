
// Image type
interface AccessHistoryImage {
    id: number;
    image: string;
    order: number;
}

// User type
interface AccessHistoryUser {
    id: number;
    first_name: string;
    last_name: string;
    employe_number: string;
    role: string;
}

// Gate type
interface AccessHistoryGate {
    id: number;
    name: string;
    role: string;
}

// Area type
interface AccessHistoryArea {
    id: number;
    name: string;
}

// Main Access History type
export interface AccessHistory {
    id: number;
    user: AccessHistoryUser;
    gate: AccessHistoryGate;
    area: AccessHistoryArea;
    status: string;
    images: AccessHistoryImage[];
    confidence: number;
    timestamp: string;
}

// API Response wrapper
export interface AccessHistoryResponse {
    success: boolean;
    message: string;
    data: {
        access_history: AccessHistory;
    };
}