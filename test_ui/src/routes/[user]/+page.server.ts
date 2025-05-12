import { fail } from '@sveltejs/kit';
import type { Actions } from './$types';
import { createRoom } from '$lib/api';

export const actions = {
	createRoom: async ({ request }) => {
		const data = await request.formData();
		const token = data.get('token') as string;
		const username = data.get('username') as string;
		const roomType = data.get('roomType') as string;
		const remoteUser = data.get('remoteUser') as string;

		console.log("createRoom: ", token, username, roomType, remoteUser);
		// missing status code
		if (token === null || username === null || roomType === null)
			return fail(400, { missing: true });

		if (roomType === "private" && remoteUser === null)
			return fail(400, { missing: true });

		let res = await createRoom(token, username, {
			room_type: roomType,
			participants: roomType === "private" ? [remoteUser] : []
		});

		if (res === undefined)
			return fail(500, { error: true });

		return {
			success: true
		}
	}
} satisfies Actions
