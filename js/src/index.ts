import { Container, getRandom } from "@cloudflare/containers";
import { Hono } from "hono";

/**
 * AssistContainer - Custom container class for the Assist Service
 * Extends Cloudflare's Container class with lifecycle hooks and error handling
 */
export class AssistContainer extends Container {
  defaultPort = 8080;

  /**
   * Error handler - logs container errors
   */
  onError(error: unknown) {
    console.error("[AssistContainer] Error:", error);
  }

  /**
   * Startup handler - logs when container starts
   */
  onStart() {
    console.log("[AssistContainer] Container started");
  }

  /**
   * Shutdown handler - logs when container stops
   */
  onStop() {
    console.log("[AssistContainer] Container stopped");
  }
}

/**
 * Hono application for routing requests to containers
 * Implements load balancing across multiple container instances
 */
const app = new Hono<{
  Bindings: { ASSIST_CONTAINER: DurableObjectNamespace<AssistContainer> };
}>();

/**
 * Load balance all requests across multiple containers
 * Uses random selection to distribute traffic across 3 container instances
 * 
 * You can adjust the number of containers by changing the second parameter
 * in getRandom() (default is 3 for load balancing)
 */
app.all("*", async (c) => {
  try {
    // Get a random container from the pool (3 instances)
    const container = await getRandom(c.env.ASSIST_CONTAINER, 3);
    
    // Forward the request to the selected container
    return await container.fetch(c.req.raw);
  } catch (error) {
    console.error("[Worker] Error routing request:", error);
    
    // Return error response
    return new Response(
      JSON.stringify({
        error: "Service temporarily unavailable",
        message: "Unable to route request to container"
      }),
      {
        status: 503,
        headers: { "Content-Type": "application/json" }
      }
    );
  }
});

export default app;
