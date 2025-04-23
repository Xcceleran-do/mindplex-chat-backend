import { error, redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { getRoomMessages, getRoomParticipants, getRoom } from '$lib/api';

export const load: PageServerLoad = async ({ params, parent }) => {
	// Get query parameter
	
	let parentData = await parent()

	if (parentData.user == null) 
		throw redirect(302, '/');

	const room = await getRoom(parentData.token, parentData.username, params.room);

	if (room == undefined)
		throw redirect(302, `/${parentData.username}`);

	const participants = await getRoomParticipants(parentData.token, parentData.username, room.id);
	const messages = await getRoomMessages(parentData.token, parentData.username, room.id);

	return {
		currentRoom: room,
		currentRoomParticipants: participants,
		currentRoomMessages: messages
	}
};

