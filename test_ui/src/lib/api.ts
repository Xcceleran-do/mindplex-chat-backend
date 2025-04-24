import type { Message, Room, ChatUser } from "$lib/types";
import { PUBLIC_CHAT_BACKEND_HOST } from "$env/static/public";

export const BACKEND_HOST= PUBLIC_CHAT_BACKEND_HOST

async function fetchChatBackend(
	path: string,
	fetchParams: RequestInit = {},
	token: string,
	username: string
) : Promise<any | undefined> {

	fetchParams.headers = {
		"Content-Type": "application/json",
		"Authorization": `Bearer ${token}`,
		"X-Username": username,
		...fetchParams.headers,
	};
	console.log("backend host: ", BACKEND_HOST);
	const response = await fetch(`${BACKEND_HOST}/${path}`, fetchParams);

	if (response.status != 200) {
		console.error("ChatBackendError: " + response.status + " " + response.statusText);
		try {
			console.log(await response.json());
		} catch {
			console.log(await response.text());
		}
		console.log("-".repeat(50));
		return
	}

	const data = await response.json();
	return data;
}

export async function getMe(token: string, username: string): Promise<ChatUser> {
	return await fetchChatBackend("users/me", {}, token, username);
}

export async function getUserByUsername(
	token: string,
	username: string,
	remoteUsername: string
) : Promise<ChatUser | undefined> {
	let user = await fetchChatBackend(`users?remote_id=${remoteUsername}`, {}, token, username);

	if (user === undefined || user.length == 0) return
	return user[0]
}

export async function getRooms(token: string, username: string, qs: string="") : Promise<Room[]> {
	return await fetchChatBackend(`rooms/?${qs}`, {}, token, username);
}

export async function getRoom(token: string, username: string, roomId: string) : Promise<Room | undefined> {
	return await fetchChatBackend(`rooms/${roomId}`, {}, token, username);
}

export async function getRoomParticipants(token: string, username: string, roomId: string) : Promise<ChatUser[]> {
	const participants = await fetchChatBackend(`rooms/${roomId}/participants`, {}, token, username);

	if (participants === undefined)
		return []

	return participants
}

export async function getRoomMessages(token: string, username: string, roomId: string) : Promise<Message[]> {
	const messages = await fetchChatBackend(`rooms/${roomId}/messages`, {}, token, username);

	if (messages === undefined)
		return []

	return messages
}

export async function createRoom(
	token: string,
	username: string,
	data: any,
) : Promise<Room | undefined> {

	return await fetchChatBackend(
		"rooms",
		{
			method: "POST", 
			body: JSON.stringify(data)
		},
		token,
		username
	);
}

export async function getOrCreatePrivateRoom(
	token: string,
	username: string,
	remoteChatUser: ChatUser, 
) : Promise<Room | undefined> {
	let room: Room[] | undefined;
	// get and return room
	room = await fetchChatBackend(
		`rooms?peer__id=${remoteChatUser.id}`,
		{},
		token,
		username
	)
	if (room !== undefined && room.length > 0) return room[0]

	// create and return room
	return await createRoom(token, username, {
		room_type: "private",
		participants: [remoteChatUser.remote_id]
	} );
}
