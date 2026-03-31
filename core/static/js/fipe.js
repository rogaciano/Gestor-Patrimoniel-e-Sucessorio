document.addEventListener('DOMContentLoaded', function () {
    const tipoSelect = document.getElementById('id_tipo');
    const marcaSelect = document.getElementById('id_marca');
    const modeloSelect = document.getElementById('id_modelo');
    const anoModeloSelect = document.getElementById('id_ano_modelo');
    const valorInput = document.getElementById('id_valor_mercado_atual');
    const fipeInput = document.getElementById('id_codigo_fipe');
    const anoFabInput = document.getElementById('id_ano_fabricacao');
    const naturezaSelect = document.getElementById('id_natureza_bem');

    const BASE_URL = 'https://parallelum.com.br/fipe/api/v1';

    // Helper to clear generic select
    function clearSelect(select, placeholder) {
        select.innerHTML = `<option value="">${placeholder}</option>`;
        select.disabled = true;
    }

    // Helper to add options
    function populateSelect(select, data, valueKey = 'nome', codeKey = 'codigo') {
        data.forEach(item => {
            const option = document.createElement('option');
            option.value = item[valueKey]; // Save Name in DB
            option.text = item[valueKey];
            option.dataset.code = item[codeKey]; // Use Code for API
            select.appendChild(option);
        });
        select.disabled = false;
    }

    // Find code by name in select options (for edit mode)
    function findCodeByName(select, name) {
        for (let option of select.options) {
            if (option.value === name) return option.dataset.code;
        }
        return null;
    }

    // 1. Fetch Brands
    async function fetchMarcas(selectedMarcaName = null) {
        const tipo = tipoSelect.value;
        if (!tipo) return;

        try {
            const response = await fetch(`${BASE_URL}/${tipo}/marcas`);
            const data = await response.json();

            clearSelect(marcaSelect, 'Selecione a Marca');
            clearSelect(modeloSelect, 'Selecione o Modelo');
            clearSelect(anoModeloSelect, 'Selecione o Ano');

            populateSelect(marcaSelect, data);

            if (selectedMarcaName) {
                marcaSelect.value = selectedMarcaName;
                const marcaCode = findCodeByName(marcaSelect, selectedMarcaName);
                if (marcaCode) fetchModelos(marcaCode, modeloSelect.dataset.initial);
            }
        } catch (error) {
            console.error('Erro ao buscar marcas:', error);
        }
    }

    // 2. Fetch Models
    async function fetchModelos(marcaCode, selectedModeloName = null) {
        const tipo = tipoSelect.value;
        try {
            const response = await fetch(`${BASE_URL}/${tipo}/marcas/${marcaCode}/modelos`);
            const data = await response.json();

            clearSelect(modeloSelect, 'Selecione o Modelo');
            clearSelect(anoModeloSelect, 'Selecione o Ano');

            populateSelect(modeloSelect, data.modelos); // API returns { modelos: [], anos: [] }

            if (selectedModeloName) {
                modeloSelect.value = selectedModeloName;
                const modeloCode = findCodeByName(modeloSelect, selectedModeloName);
                if (modeloCode) fetchAnos(marcaCode, modeloCode, anoModeloSelect.dataset.initial);
            }
        } catch (error) {
            console.error('Erro ao buscar modelos:', error);
        }
    }

    // 3. Fetch Years
    async function fetchAnos(marcaCode, modeloCode, selectedAnoCode = null) {
        if (!tipoSelect) return;
        const tipo = tipoSelect.value;
        try {
            const response = await fetch(`${BASE_URL}/${tipo}/marcas/${marcaCode}/modelos/${modeloCode}/anos`);
            const data = await response.json();

            clearSelect(anoModeloSelect, 'Selecione o Ano');

            // Populate with split logic
            data.forEach(item => {
                const option = document.createElement('option');
                // item.nome = "2015 Gasolina", item.codigo = "2015-1"
                // Extract year from label or code. Code "2015-1" -> 2015.
                // Exception: "32000-1" (Zero KM) -> How to handle?
                // Usually "32000" is code for Zero KM in FIPE API sometimes? 
                // Let's rely on the first 4 digits of the Label if it looks like a year.

                const yearMatch = item.nome.match(/^\d{4}/);
                const yearInt = yearMatch ? yearMatch[0] : 0; // Default to 0 if not found (e.g. Zero KM)

                option.value = yearInt; // Save "2015" for DB IntegerField
                option.text = item.nome;
                option.dataset.code = item.codigo; // "2015-1" for API

                anoModeloSelect.appendChild(option);
            });
            anoModeloSelect.disabled = false;

            if (selectedAnoCode) {
                // For edit mode, we might need logic to match "2015" to "2015-1" option
                // But selectedAnoCode passed here might be the DB value "2015".
                // So we select by value.
                anoModeloSelect.value = selectedAnoCode;
            }
        } catch (error) {
            console.error('Erro ao buscar anos:', error);
        }
    }

    // 4. Fetch Details
    async function fetchDetalhes(marcaCode, modeloCode, anoCode) {
        if (!tipoSelect) return;
        const tipo = tipoSelect.value;
        try {
            const response = await fetch(`${BASE_URL}/${tipo}/marcas/${marcaCode}/modelos/${modeloCode}/anos/${anoCode}`);
            const data = await response.json();

            // Populate Fields
            if (valorInput) {
                const valorClean = data.Valor.replace('R$ ', '').replace('.', '').replace(',', '.');
                valorInput.value = valorClean;
            }
            if (fipeInput) fipeInput.value = data.CodigoFipe;
            if (anoFabInput) {
                // Optional: Auto-fill manuf year same as model, user calls verify
                if (!anoFabInput.value) anoFabInput.value = data.AnoModelo;
            }

        } catch (error) {
            console.error('Erro ao buscar detalhes:', error);
        }
    }

    // Safety check
    if (!marcaSelect || !modeloSelect) return;

    // --- Event Listeners ---

    // Tipo Change
    tipoSelect.addEventListener('change', () => fetchMarcas());

    // Marca Change
    marcaSelect.addEventListener('change', function () {
        const selectedOption = this.options[this.selectedIndex];
        const marcaCode = selectedOption.dataset.code;
        if (marcaCode) fetchModelos(marcaCode);
    });

    // Modelo Change
    modeloSelect.addEventListener('change', function () {
        // Need marcaCode
        const marcaOption = marcaSelect.options[marcaSelect.selectedIndex];
        const marcaCode = marcaOption.dataset.code;

        const selectedOption = this.options[this.selectedIndex];
        const modeloCode = selectedOption.dataset.code;

        if (marcaCode && modeloCode) fetchAnos(marcaCode, modeloCode);
    });

    // Ano Change
    anoModeloSelect.addEventListener('change', function () {
        if (!marcaSelect.options[marcaSelect.selectedIndex] || !modeloSelect.options[modeloSelect.selectedIndex]) return;

        const marcaCode = marcaSelect.options[marcaSelect.selectedIndex].dataset.code;
        const modeloCode = modeloSelect.options[modeloSelect.selectedIndex].dataset.code;
        // Use the FIPE Code stored in dataset, not the value (which is Year Int)
        const selectedOption = this.options[this.selectedIndex];
        const anoCode = selectedOption.dataset.code;

        if (marcaCode && modeloCode && anoCode) {
            fetchDetalhes(marcaCode, modeloCode, anoCode);
        }
    });

    // Initialization
    if (tipoSelect.value) {
        // If editing, we have values.
        // But we don't have the Codes (they are not stored).
        // So we trigger the fetch chain, matching by Name.
        // Store initial values to match
        marcaSelect.dataset.initial = marcaSelect.value; // BUT wait, standard rendering populates 'value' with DB value.
        // Since I changed widget to Select, Django renders a Select with 1 option (the current value)?
        // No, choices are empty in forms.py (except for tipo).
        // So Django renders an empty select or a select with the current value as the only option?
        // Actually since choices are empty, it might render nothing or just the current value if it's valid?
        // Since it's a ModelForm, and I overrode the widget but not the choices (except for valid ones?), 
        // Django might not render the current value if it's not in choices.

        // Strategy: First fetch fills options. Then we select the one matching DB value.
        fetchMarcas(marcaSelect.getAttribute('value')); // HTML 'value' attribute might be set by Django
    } else {
        fetchMarcas(); // Init default
    }

});
