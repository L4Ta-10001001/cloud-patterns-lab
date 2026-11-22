package com.example.pedidos;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.example.pedidos.RestauranteService.RespuestaPedido;

@RestController
public class PedidosController {

	private final RestauranteService restauranteService;

	public PedidosController(RestauranteService restauranteService) {
		this.restauranteService = restauranteService;
	}

	@GetMapping("/pedidos/1")
	public RespuestaPedido consultarRestaurante(
			@RequestParam(defaultValue = "false") boolean fallar) {
		return restauranteService.consultarRestaurante(fallar);
	}
}
