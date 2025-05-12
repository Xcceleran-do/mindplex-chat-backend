<script lang="ts">
let name = 'world';
import { browser } from '$app/environment';

let messages: string[] = $state([]);

if (browser) {
	const evtSource = new EventSource("http://localhost:9010/sse/stream");
	evtSource.onmessage = function(event) {
		//console.log(event);
		messages.push(event.data);
	}
}


</script>

<h1>Hello {name}!</h1>


<details>
	<summary>How this works</summary>
	<small>This site opens a Server-Sent Event (SSE) Source and then updates the page when the server sends any events.  Default event time on sse.dev is 2 seconds<br>
		See more at <a target="_blank" href="http://localhost:9010/sse/stream">https://sse.dev/</a>
	</small>

</details>

{#each messages as m}
	<p>
		{m}
	</p>
{/each}
