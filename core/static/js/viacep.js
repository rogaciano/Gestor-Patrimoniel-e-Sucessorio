/**
 * Integração com ViaCEP
 * Autocompleta endereço ao digitar CEP
 */

document.addEventListener('DOMContentLoaded', function () {
    const cepInput = document.querySelector('input[name="cep"]');

    if (cepInput) {
        cepInput.addEventListener('blur', function () {
            const cep = this.value.replace(/\D/g, '');

            if (cep.length === 8) {
                // Mostra loading
                cepInput.classList.add('opacity-50');

                fetch(`https://viacep.com.br/ws/${cep}/json/`)
                    .then(response => response.json())
                    .then(data => {
                        if (!data.erro) {
                            // Preenche campos
                            document.querySelector('input[name="logradouro"]').value = data.logradouro || '';
                            document.querySelector('input[name="bairro"]').value = data.bairro || '';
                            document.querySelector('input[name="cidade"]').value = data.localidade || '';
                            document.querySelector('select[name="uf"]').value = data.uf || '';

                            // Foca no número
                            document.querySelector('input[name="numero"]').focus();
                        } else {
                            alert('CEP não encontrado. Verifique e tente novamente.');
                        }
                    })
                    .catch(error => {
                        console.error('Erro ao buscar CEP:', error);
                        alert('Erro ao consultar CEP. Verifique sua conexão.');
                    })
                    .finally(() => {
                        cepInput.classList.remove('opacity-50');
                    });
            }
        });
    }
});
