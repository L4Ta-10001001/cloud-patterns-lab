package com.example.restaurantes;

import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class RestauranteController {

	@GetMapping("/restaurantes/1")
	public Map<String, Object> obtenerRestaurante(
			@RequestParam(defaultValue = "false") boolean fallar) {
		if (fallar) {
			throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR,
					"Fallo simulado del servicio Restaurantes");
		}

		return Map.of("id", 1, "nombre", "Pizzeria Central", "disponible", true);
	}
}
