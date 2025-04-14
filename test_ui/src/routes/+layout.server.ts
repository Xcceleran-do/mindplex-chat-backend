
import type { LayoutServerLoad } from './$types';
import { testUsers } from '$lib/';

export const load: LayoutServerLoad = async () => {
	return {
		allUsers: Object.keys(testUsers)
	}
}
