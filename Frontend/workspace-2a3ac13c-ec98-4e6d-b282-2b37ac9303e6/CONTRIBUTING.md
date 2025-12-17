# Contribuindo para o BHub Frontend

Obrigado por seu interesse em contribuir para o frontend do BHub! Este guia irá ajudar você a começar.

## 🚀 Como Começar

### Pré-requisitos
- Node.js 18+
- npm ou yarn
- Conhecimento básico de React/Next.js
- Familiaridade com TypeScript
- Conhecimento de Tailwind CSS

### Setup do Ambiente
```bash
# 1. Fork o repositório
git clone https://github.com/seu-usuario/bhub-frontend.git
cd bhub-frontend

# 2. Instale as dependências
npm install

# 3. Inicie o servidor de desenvolvimento
npm run dev
```

## 📁 Estrutura do Projeto

Entenda a estrutura do projeto antes de começar:

```
src/
├── app/              # App Router (Next.js 15)
├── components/        # Componentes React
├── pages/           # Páginas principais
├── store/           # Zustand stores
├── services/        # Serviços de API
├── types/           # Tipos TypeScript
├── lib/             # Utilitários
└── hooks/           # Hooks personalizados
```

## 🎨 Guia de Estilo

### Cores BHub
Use as cores personalizadas do BHub:
```css
bg-bhub-teal-primary    /* #41B5A3 */
bg-bhub-navy-dark      /* #1C3159 */
bg-bhub-red-accent     /* #BA213D */
bg-bhub-yellow-primary  /* #FABD4A */
```

### Tipografia
- **Títulos**: `font-display font-bold`
- **Corpo**: `font-body font-light`
- **Secundário**: `font-body font-normal text-sm`

### Componentes
Use os componentes existentes sempre que possível:
- `<Badge>` para categorias
- `<Avatar>` para fotos de perfil
- `<Button>` para ações
- `<Icon>` para ícones

## 🔄 Fluxo de Trabalho

### 1. Crie uma Branch
```bash
git checkout -b feature/sua-feature
```

### 2. Desenvolva
- Siga os padrões de código existentes
- Use TypeScript estrito
- Teste em diferentes tamanhos de tela
- Verifique a acessibilidade

### 3. Teste
```bash
# Verifique o código
npm run lint

# Teste a build
npm run build
```

### 4. Commit
```bash
git add .
git commit -m "feat: adiciona nova funcionalidade"
```

### 5. Pull Request
- Abra uma PR para a branch `main`
- Descreva as mudanças claramente
- Adicione screenshots se aplicável

## 🏗️ Tipos de Contribuição

### 🐛 Bug Reports
- Use o template de issue para bugs
- Inclua passos para reproduzir
- Adicione screenshots se possível
- Mencione o navegador e versão

### ✨ Novas Funcionalidades
- Abra uma issue antes de começar
- Descreva a funcionalidade proposta
- Discuta a implementação

### 🎨 Melhorias de UI/UX
- Reporte problemas de usabilidade
- Sugira melhorias no design
- Inclua exemplos visuais

### 📚 Documentação
- Melhore a documentação existente
- Adicione exemplos de código
- Documente novos componentes

### 🧪 Testes
- Escreva testes unitários
- Testes de integração
- Testes E2E para fluxos críticos

## 📋 Padrões de Código

### Componentes React
```tsx
// ✅ Bom
interface ComponentProps {
  title: string;
  onAction?: () => void;
}

export function Component({ title, onAction }: ComponentProps) {
  return (
    <div className="bg-white p-4 rounded">
      <h2 className="font-display font-bold">{title}</h2>
      <Button onClick={onAction}>Ação</Button>
    </div>
  );
}
```

### TypeScript
- Use tipos estritos
- Evite `any`
- Prefira interfaces para objetos
- Use tipos union para valores fixos

### Estilos
- Use classes Tailwind
- Evite estilos inline
- Prefira responsividade mobile-first
- Use as cores BHub personalizadas

## 🧪 Testes

### Unitários
```bash
# Execute testes unitários
npm run test
```

### E2E
```bash
# Execute testes end-to-end
npm run test:e2e
```

## 📱 Responsividade

### Breakpoints
- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px

### Diretrizes
- Design mobile-first
- Teste em múltiplos dispositivos
- Use layouts flexbox/grid
- Evite tamanhos fixos

## ♿ Acessibilidade

### Requisitos
- Contraste mínimo WCAG AA
- Navegação por teclado
- ARIA labels apropriados
- Semântica HTML5 correta

### Checklist
- [ ] Uso de heading hierarchy
- [ ] Alt text em imagens
- [ ] Focus indicators visíveis
- [ ] Skip links para navegação
- [ ] Role attributes apropriados

## 🚀 Deploy

### Build
```bash
npm run build
```

### Preview
```bash
npm run build && npm run preview
```

## 📝 Comunicação

### Commit Messages
Use o formato Conventional Commits:
```
feat: nova funcionalidade
fix: correção de bug
docs: documentação
style: formatação de código
refactor: refatoração
test: testes
chore: mudanças de build/process
```

### Pull Requests
- Título descritivo
- Descrição detalhada
- Screenshots se aplicável
- Link para issues relacionadas

## 🤝 Código de Conduta

### Seja Respeitoso
- Trate todos com respeito
- Seja construtivo em feedbacks
- Aceite diferentes opiniões
- Ajude outros contribuidores

### Comunicação
- Use linguagem profissional
- Seja claro e conciso
- Evite jargões excessivos
- Mantenha o foco técnico

## 🏆 Reconhecimento

Contribuidores serão reconhecidos em:
- README.md
- Release notes
- Seção de contribuidores

## ❓ Dúvidas

- Verifique issues existentes
- Leia a documentação
- Participe das discussões
- Contate os mantenedores

---

**Obrigado por contribuir para o BHub!** 🎉