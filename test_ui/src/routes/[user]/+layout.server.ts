import { error } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';
import { testUsers } from '$lib/';

const AUTH_BACKEND_HOST = "staging.mindplex.ai"

async function auth_user(username: string) {
	// get password or null/undefined
	const userPassword = testUsers[username]
	let token : string | null = null;
	

	if (userPassword === undefined) {
		// no user return undefined instead of token 
		token = null
	} else {
		// authenticate user and return token

		let response = await fetch(`https://${AUTH_BACKEND_HOST}/wp-json/auth/v1/token`, {
			method: "POST",
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				"username": "dave",
				"password": "iBD9xSztMP8C!WglcdzyH2bq",
				"login_with": "email_password",
				"login_from": "Android"
			})
		})

		const data = await response.json()
		token = data.token
	}

	return token
}


export const load: LayoutServerLoad = async ({ url, params }) => {
	// Get query parameter

	const username = params.user;
	let user: { username: string, token: string } | null = null

	const token = await auth_user(username as string);

	if (token !== null ) {
		user = {
			username: username as string,
			token: token
		}
	};

	return {
		user: user,
	};
};


