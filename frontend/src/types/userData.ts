import { Area } from "./area";
import { ReferenceImage } from "./referenceImage";

export interface UserData {
    id: string;
    first_name: string;
    last_name: string;
    employe_number: string;
    national_id: string;
    phone_number: string;
    role: string;
    areas: Area[];
    reference_images: ReferenceImage[];
    is_active: boolean;
    profile_image: string;
    must_change_password: boolean;
}