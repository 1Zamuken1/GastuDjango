from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm

def login_view(request):
    return render(request, 'landing/login.html')

def register_view(request):
    """Vista de registro de nuevos usuarios.

    La plantilla original se encontraba dentro de la aplicación **landing**
    (landing/templates/landing/register.html). Django buscaba `usuarios/register.html`
    porque así se especificaba aquí, por eso se producía el error
    ``TemplateDoesNotExist``.  Para reutilizar el diseño de landing basta con
    indicar la ruta correcta o, alternativamente, mover el fichero a
    ``usuarios/templates/usuarios/register.html``.
    """

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()

    # renderizamos el HTML de landing en lugar de uno inexistente en usuarios
    return render(request, 'landing/register.html', {'form': form})