package com.example.pedidos;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;

@Service
public class RestauranteService {

	private final RestClient restClient;
	private final CircuitBreakerRegistry circuitBreakerRegistry;

	public RestauranteService(@Value("${restaurantes.base-url}") String baseUrl,
			CircuitBreakerRegistry circuitBreakerRegistry) {
		this.restClient = RestClient.builder().baseUrl(baseUrl).build();
		this.circuitBreakerRegistry = circuitBreakerRegistry;
	}

	@CircuitBreaker(name = "restaurantes", fallbackMethod = "restauranteNoDisponible")
	public RespuestaPedido consultarRestaurante(boolean fallar) {
		RestauranteResponse restaurante = restClient.get()
				.uri(uriBuilder -> uriBuilder.path("/restaurantes/1")
						.queryParam("fallar", fallar).build())
				.retrieve()
				.body(RestauranteResponse.class);

		return new RespuestaPedido(restaurante,
				"El restaurante está disponible para recibir pedidos.", estadoActual());
	}

	private RespuestaPedido restauranteNoDisponible(boolean fallar, Throwable excepcion) {
		String estado = estadoActual();
		String mensaje = "El servicio de restaurantes no está disponible temporalmente.";
		if (excepcion instanceof CallNotPermittedException) {
			mensaje += " El circuito está OPEN; se omitió la llamada a Restaurantes.";
		}
		return new RespuestaPedido(null, mensaje, estado);
	}

	private String estadoActual() {
		return circuitBreakerRegistry.circuitBreaker("restaurantes").getState().name();
	}

	public record RespuestaPedido(RestauranteResponse restaurante, String mensaje, String estadoCircuito) {
	}
}
