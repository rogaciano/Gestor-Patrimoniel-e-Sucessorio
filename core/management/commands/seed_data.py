from django.core.management.base import BaseCommand, CommandError

from core.seeders.demo_data import DemoSeeder


class Command(BaseCommand):
    help = "Cria ou recria massa de dados demo para testes locais."

    def add_arguments(self, parser):
        parser.add_argument(
            "--families",
            type=int,
            default=5,
            help="Quantidade de famílias demo a criar.",
        )
        parser.add_argument(
            "--min-members",
            type=int,
            default=3,
            help="Quantidade mínima de membros por família.",
        )
        parser.add_argument(
            "--max-members",
            type=int,
            default=8,
            help="Quantidade máxima de membros por família.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=20260331,
            help="Semente para gerar dados determinísticos.",
        )

    def handle(self, *args, **options):
        families = options["families"]
        min_members = options["min_members"]
        max_members = options["max_members"]
        seed = options["seed"]

        if families < 1:
            raise CommandError("--families deve ser maior que zero.")
        if min_members < 3:
            raise CommandError("--min-members deve ser pelo menos 3.")
        if min_members > max_members:
            raise CommandError("--min-members não pode ser maior que --max-members.")

        self.stdout.write("Gerando massa de dados demo reutilizável...")

        seeder = DemoSeeder(
            families=families,
            min_members=min_members,
            max_members=max_members,
            seed=seed,
        )
        summary = seeder.run()

        self.stdout.write(
            self.style.SUCCESS(
                "Seed concluído: "
                f"{summary['familias']} famílias, "
                f"{summary['pessoas']} pessoas, "
                f"{summary['holdings']} holdings, "
                f"{summary['participacoes']} participações, "
                f"{summary['imoveis']} imóveis, "
                f"{summary['veiculos']} veículos, "
                f"{summary['investimentos']} investimentos e "
                f"{summary['empresas']} participações empresariais."
            )
        )
        self.stdout.write(
            "Dados demo anteriores removidos nesta execução: "
            f"{summary['familias_removidas']} famílias, "
            f"{summary['pessoas_removidas']} pessoas, "
            f"{summary['holdings_removidas']} holdings e "
            f"{summary['ativos_removidos']} ativos."
        )
