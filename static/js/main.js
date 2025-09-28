document.addEventListener("DOMContentLoaded", function() {
    // Pegando os elementos do HTML
    var modal = document.getElementById("imageModal");
    var img = document.getElementById("grafico-img");
    var modalImg = document.getElementById("modalImage");
    var closeButton = document.getElementsByClassName("close-button")[0];

    // Verificando a existência da imagem do gráfico na página
    if (img) {
        // Abrindo o modal quando o usuário clica na imagem
        img.onclick = function() {
            modal.style.display = "block";
            modalImg.src = this.src;
        }
    }

    // Fecha o modal no "X"
    if (closeButton) {
        closeButton.onclick = function() {
            modal.style.display = "none";
        }
    }

    // Fecha o modal ao clicar fora da imagem
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }
});