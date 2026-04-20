import sys

with open('templates/weekly_summary.html', 'r', encoding='utf-8') as f:
    content = f.read()

old1 = """                <div class="text-center py-3">
                    <div class="spinner-border spinner-border-sm text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>"""
new1 = """                <div class="skeleton mt-2" style="height: 100px; width: 100%;"></div>"""

old2 = """    tableBody.innerHTML = `
        <tr>
            <td colspan="6" class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </td>
        </tr>`;"""
new2 = """    tableBody.innerHTML = `
        <tr>
            <td colspan="6">
                <div class="skeleton" style="height: 150px; width: 100%;"></div>
            </td>
        </tr>`;"""

content = content.replace(old1, new1)
content = content.replace(old2, new2)

with open('templates/weekly_summary.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Replaced successfully!')
