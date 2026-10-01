"""Catálogo de checks: validação, versão, hash, dependências e conferência de citação."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from coscip_normative import parse_markdown
from coscip_normative.verification import (
    CatalogError,
    CheckValidationError,
    load_catalog,
    parse_check,
    verify_catalog,
)

CHECKS = Path(__file__).resolve().parents[2] / "normative" / "checks"


def minimal(**kwargs) -> dict:
    base = {
        "schema_version": "checks/1.0",
        "id": "X-001", "version": 1, "title": "Exemplo", "system": "EXEMPLO",
        "type": "DOCUMENT_PRESENCE", "publication_state": "DRAFT",
        "production_eligible": False,
        "question": {"kind": "presence", "field": "documento"},
        "normative_basis": [{"document": "NT 9-99", "edition": "1ª", "item": "1.1",
                             "quote": ["exemplo"]}],
        "wording": {"title": "Documento não localizado"},
    }
    base.update(kwargs)
    return base


def test_catalogo_real_carrega_e_e_deterministico():
    catalogo = load_catalog(CHECKS)
    outro = load_catalog(CHECKS)
    assert catalogo.publication_state == "DRAFT"
    assert len(catalogo.checks) == 21
    assert catalogo.content_sha256 == outro.content_sha256


def test_hash_do_catalogo_muda_quando_um_check_muda(tmp_path):
    origem = load_catalog(CHECKS)
    destino = tmp_path / "checks"
    destino.mkdir()
    manifesto = yaml.safe_load((CHECKS / "catalogo.yaml").read_text(encoding="utf-8"))
    for relativo in manifesto["checks"]:
        alvo = destino / relativo
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text((CHECKS / relativo).read_text(encoding="utf-8"), encoding="utf-8")
    alterado = yaml.safe_load((destino / manifesto["checks"][0]).read_text(encoding="utf-8"))
    alterado["severity"] = "MINOR"
    (destino / manifesto["checks"][0]).write_text(yaml.safe_dump(alterado), encoding="utf-8")
    (destino / "catalogo.yaml").write_text(yaml.safe_dump(manifesto), encoding="utf-8")
    assert load_catalog(destino).content_sha256 != origem.content_sha256


def test_rascunho_nao_pode_ir_a_producao():
    with pytest.raises(CheckValidationError, match="produção"):
        parse_check(minimal(production_eligible=True))


def test_check_executavel_exige_base_normativa():
    with pytest.raises(CheckValidationError, match="base normativa"):
        parse_check(minimal(normative_basis=[]))


def test_citacao_sem_termos_de_conferencia_e_recusada():
    dados = minimal()
    dados["normative_basis"][0].pop("quote")
    with pytest.raises(CheckValidationError, match="termos de conferência"):
        parse_check(dados)


def test_pergunta_exige_os_campos_que_usa():
    with pytest.raises(CheckValidationError, match="minimum_count"):
        parse_check(minimal(type="CAD_COUNT",
                            question={"kind": "minimum_count", "field": "extintor"}))


def test_check_manual_nao_tem_pergunta_e_vice_versa():
    manual = parse_check(minimal(type="MANUAL_CONFIRMATION", question=None,
                                 normative_basis=[]))
    assert manual.manual is True
    with pytest.raises(CheckValidationError, match="MANUAL_CONFIRMATION"):
        parse_check(minimal(type="MANUAL_CONFIRMATION"))
    with pytest.raises(CheckValidationError, match="MANUAL_CONFIRMATION"):
        parse_check(minimal(question=None))


def test_ausencia_nunca_pode_concluir_conformidade():
    for campo in ("missing_required_field", "conflicting_values", "quality_gate_failed"):
        with pytest.raises(CheckValidationError, match="COMPLIANT"):
            parse_check(minimal(result_rules={campo: "COMPLIANT"}))


def test_catalogo_recusa_check_duplicado(tmp_path):
    _escrever(tmp_path, [minimal(), minimal()])
    with pytest.raises(CatalogError, match="duplicado"):
        load_catalog(tmp_path)


def test_catalogo_recusa_dependencia_inexistente(tmp_path):
    _escrever(tmp_path, [minimal(depends_on=["NAO-EXISTE"])])
    with pytest.raises(CatalogError, match="inexistente"):
        load_catalog(tmp_path)


def test_catalogo_recusa_ciclo(tmp_path):
    _escrever(tmp_path, [minimal(id="A-1", depends_on=["A-2"]),
                         minimal(id="A-2", depends_on=["A-1"])])
    with pytest.raises(CatalogError, match="ciclo"):
        load_catalog(tmp_path)


def test_catalogo_recusa_caminho_fora_da_pasta(tmp_path):
    (tmp_path / "catalogo.yaml").write_text(yaml.safe_dump({
        "schema_version": "check-catalog/1.0", "id": "c", "name": "c", "version": 1,
        "jurisdiction": "CBMERJ-RJ", "publication_state": "DRAFT",
        "checks": ["../fora.yaml"]}), encoding="utf-8")
    with pytest.raises(CatalogError, match="fora do catálogo"):
        load_catalog(tmp_path)


def test_catalogo_recusa_arquivo_vazio(tmp_path):
    (tmp_path / "catalogo.yaml").write_text(yaml.safe_dump({
        "schema_version": "check-catalog/1.0", "id": "c", "name": "c", "version": 1,
        "jurisdiction": "CBMERJ-RJ", "publication_state": "DRAFT",
        "checks": ["vazio.yaml"]}), encoding="utf-8")
    (tmp_path / "vazio.yaml").write_text("", encoding="utf-8")
    with pytest.raises(CatalogError, match="vazio ou inválido"):
        load_catalog(tmp_path)


def test_matriz_de_evidencias_sai_dos_metadados():
    linhas = {linha["check"]: linha for linha in load_catalog(CHECKS).evidence_matrix()}
    assert "ART" in linhas["HID-DOC-004"]["accepted_evidence"]
    assert linhas["QG-CAD-WALLS"]["manual"] is True


def _fonte_sintetica(texto: str):
    bruto = ("---\ndocumento: NT 9-99\nedicao: 1ª\n---\n## Página 1\n"
             f"1.1 {texto}\n").encode()
    return parse_markdown(bruto, "nt-9-99-exemplo.md")


def _escrever(pasta: Path, checks: list[dict]) -> None:
    nomes = []
    for i, dados in enumerate(checks):
        nome = f"check-{i}.yaml"
        (pasta / nome).write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
        nomes.append(nome)
    (pasta / "catalogo.yaml").write_text(yaml.safe_dump({
        "schema_version": "check-catalog/1.0", "id": "c", "name": "c", "version": 1,
        "jurisdiction": "CBMERJ-RJ", "publication_state": "DRAFT", "checks": nomes}),
        encoding="utf-8")


def test_conferencia_de_citacao_reprova_termo_ausente(tmp_path):
    dados = deepcopy(minimal())
    _escrever(tmp_path, [dados])
    catalogo = load_catalog(tmp_path)
    fonte = _fonte_sintetica("texto que não contém o termo procurado")
    relatorio = verify_catalog(catalogo, {fonte.document: fonte})
    assert relatorio["verified"] is False
    assert "X-001" in relatorio["failures"][0]


def test_conferencia_de_citacao_aprova_termo_presente(tmp_path):
    _escrever(tmp_path, [minimal()])
    catalogo = load_catalog(tmp_path)
    fonte = _fonte_sintetica("este item traz o termo exemplo no meio da frase")
    relatorio = verify_catalog(catalogo, {fonte.document: fonte})
    assert relatorio["verified"] is True
    assert relatorio["catalog"]["content_sha256"] == catalogo.content_sha256
