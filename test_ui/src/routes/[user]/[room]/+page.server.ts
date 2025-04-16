import { error, redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { testUsers } from '$lib/';
import { getRooms, getRoomByUsername } from '$lib/api';

export const load: PageServerLoad = async ({ params, parent }) => {
	// Get query parameter
	
	let parentData = await parent()

	const username = params.user;
	const remoteUser = params.room;

	if (parentData.user == null) {
		// redirect to home page
		throw redirect(302, '/');
	}

	let privateRoom 

	console.log("currentUserRooms: ", currentUserRooms)

	return {
		remoteUser,
		currentUserRooms
	}

};

