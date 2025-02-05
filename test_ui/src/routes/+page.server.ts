import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const AUTH_BACKEND_HOST = "stagingauth.mindplex.ai"

const test_users = [
	{ username: "dave", password: "dave" },
	{ username: "tony", password: "tony" },
	{ username: "ivan", password: "ivan" },
]


async function auth_user(count = 1) {
	const user = test_users[count - 1]

	if (user === undefined) {
		throw new Error("No test user found")
	}

	const myHeaders = new Headers();
	myHeaders.append("Content-Type", "application/x-www-form-urlencoded");
	myHeaders.append("Cookie", "AWSALBAPP-0=_remove_; AWSALBAPP-1=_remove_; AWSALBAPP-2=_remove_; AWSALBAPP-3=_remove_");

	const urlencoded = new URLSearchParams();
	urlencoded.append("client_id", "mindplex");
	urlencoded.append("username", "dave");
	urlencoded.append("password", "dave");
	urlencoded.append("grant_type", "password");
	urlencoded.append("client_secret", "Dzkhw0zTnV6wgQ59Lsnqm5JaG4CreCAf");
	urlencoded.append("scope", "openid");
	urlencoded.append("", "");

	const requestOptions: RequestInit = {
		method: "POST",
		headers: myHeaders,
		body: urlencoded.toString(),
		redirect: "follow"
	};

	const res = await fetch(`https://${AUTH_BACKEND_HOST}/realms/Mindplex/protocol/openid-connect/token`, requestOptions)


	return (await res.json()).access_token as string

}


export const load: PageServerLoad = async ({ url }) => {
	// Get query parameter

	const userId = url.searchParams.get("user_id");

	if (userId === null) {
		throw error(400, "No user_id provided");
	}

	const token = await auth_user(Number(userId))

	return {
		user: {
			userId,
			token
		}
	};
};
