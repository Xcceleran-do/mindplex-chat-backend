
export interface Room {
	room_type: string;
	id: string;
	owner_id: string;
	created: string;
	last_interacted: string;
}

export interface ChatUser {
	id: string,
	remote_id: string
}

export interface Message {
	id: string;
	owner_id: string;
	text: string;
	created: string;
}


