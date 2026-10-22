import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.people import roles
from apps.people.models import Broker, Owner, Partner
from apps.properties.models import Property
from apps.properties.tests.factories import CategoryFactory, NeighborhoodFactory, PropertyFactory

pytestmark = pytest.mark.django_db
User = get_user_model()


def make_user(role, username=None, **kwargs):
    user = User.objects.create_user(username or role.lower(), password="pw", **kwargs)
    roles.apply_role(user, role)
    return user


@pytest.fixture
def login(client):
    def _login(user):
        client.force_login(user)
        return client

    return _login


def perms_of(name):
    return set(Group.objects.get(name=name).permissions.values_list("codename", flat=True))


def test_groups_created_with_expected_permissions():
    assert set(Group.objects.values_list("name", flat=True)) >= set(roles.ROLE_NAMES)
    assert {"delete_property", "change_sitesettings"} <= perms_of(roles.ADMIN)
    assert "delete_property" in perms_of(roles.MANAGER)
    assert not {"change_sitesettings", "view_user"} & perms_of(roles.MANAGER)
    assert "change_property" in perms_of(roles.BROKER)
    assert "delete_property" not in perms_of(roles.BROKER)
    assert "add_property" not in perms_of(roles.CLERK)
    assert "change_lead" in perms_of(roles.CLERK)


def test_apply_role_sets_staff_and_single_group():
    user = User.objects.create_user("x", password="pw")
    roles.apply_role(user, roles.BROKER)
    roles.apply_role(user, roles.CLERK)
    user.refresh_from_db()
    assert user.is_staff and roles.role_of(user) == roles.CLERK
    assert user.groups.count() == 1


def test_broker_sees_only_own_properties(login):
    user = make_user(roles.BROKER)
    broker = Broker.objects.create(name="B", user=user)
    mine = PropertyFactory(broker=broker)
    created = PropertyFactory(created_by=user)
    other = PropertyFactory()
    client = login(user)
    r = client.get(reverse("admin:properties_property_changelist"))
    assert {p.pk for p in r.context["cl"].result_list} == {mine.pk, created.pk}
    url = reverse("admin:properties_property_change", args=[other.pk])
    assert client.get(url).status_code in (302, 404)
    url = reverse("admin:properties_property_change", args=[mine.pk])
    assert client.get(url).status_code == 200


def test_broker_cannot_delete(login):
    user = make_user(roles.BROKER)
    prop = PropertyFactory(created_by=user)
    url = reverse("admin:properties_property_delete", args=[prop.pk])
    assert login(user).post(url, {"post": "yes"}).status_code == 403
    assert Property.objects.filter(pk=prop.pk).exists()


def test_broker_sees_only_leads_of_own_properties(login):
    from apps.leads.models import Lead

    user = make_user(roles.BROKER)
    mine = PropertyFactory(created_by=user)
    other = PropertyFactory()
    own_lead = Lead.objects.create(property=mine, name="A", email="a@a.com", message="x")
    Lead.objects.create(property=other, name="B", email="b@b.com", message="x")
    Lead.objects.create(property=None, name="C", email="c@c.com", message="x")
    r = login(user).get(reverse("admin:leads_lead_changelist"))
    assert [lead.pk for lead in r.context["cl"].result_list] == [own_lead.pk]


def test_clerk_can_read_properties_but_not_add(login):
    client = login(make_user(roles.CLERK))
    assert client.get(reverse("admin:properties_property_changelist")).status_code == 200
    assert client.get(reverse("admin:properties_property_add")).status_code == 403
    assert client.get(reverse("admin:leads_lead_changelist")).status_code == 200


def test_only_admin_reaches_team(login):
    for role, expected in [(roles.ADMIN, 200), (roles.MANAGER, 403), (roles.BROKER, 403)]:
        user = make_user(role, username=f"u-{role}")
        assert login(user).get(reverse("admin:auth_user_changelist")).status_code == expected, role
    mgr = make_user(roles.MANAGER, username="mgr2")
    r = login(mgr).get(reverse("admin:core_sitesettings_changelist"))
    assert r.status_code in (302, 403)


def test_user_form_applies_role(admin_client):
    data = {
        "username": "novo",
        "usable_password": "true",
        "password1": "S3nh@-muito-forte-99",
        "password2": "S3nh@-muito-forte-99",
        "first_name": "Novo",
        "last_name": "Usuário",
        "email": "n@n.com",
        "role": roles.BROKER,
    }
    r = admin_client.post(reverse("admin:auth_user_add"), data)
    assert r.status_code == 302
    user = User.objects.get(username="novo")
    assert user.is_staff and roles.role_of(user) == roles.BROKER
    assert not user.is_superuser and not user.user_permissions.exists()


def test_audit_fields_set_in_admin(admin_client):
    data = {
        "title": "Auditada",
        "category": CategoryFactory().pk,
        "status": "DRAFT",
        "purpose": "SALE",
        "sale_price": "300000",
        "neighborhood": NeighborhoodFactory().pk,
        "bedrooms": 1,
        "suites": 0,
        "bathrooms": 1,
        "parking_spaces": 0,
        "source": "OWN",
        "photos-TOTAL_FORMS": 0,
        "photos-INITIAL_FORMS": 0,
        "photos-MIN_NUM_FORMS": 0,
        "photos-MAX_NUM_FORMS": 1000,
    }
    assert admin_client.post(reverse("admin:properties_property_add"), data).status_code == 302
    prop = Property.objects.get(title="Auditada")
    assert prop.created_by.username == "admin" and prop.updated_by.username == "admin"
    html = admin_client.get(reverse("admin:properties_property_change", args=[prop.pk]))
    assert "cadastrado por" in html.content.decode().lower()


def test_internal_data_never_leaks_to_public_site(client):
    user = User.objects.create_user("segredo_user", first_name="Fulano", last_name="Secreto")
    broker = Broker.objects.create(name="Corretora Reservada", user=user, creci="99999-F")
    owner = Owner.objects.create(name="Dono Confidencial", document="529.982.247-25")
    partner = Partner.objects.create(name="Parceiro Oculto", company="Empresa Oculta")
    prop = PropertyFactory(
        broker=broker, owner=owner, partner=partner, created_by=user, updated_by=user
    )
    secrets = [
        "segredo_user",
        "Fulano",
        "Corretora Reservada",
        "99999-F",
        "Dono Confidencial",
        "529.982.247-25",
        "Parceiro Oculto",
        "Empresa Oculta",
    ]
    for url in (prop.get_absolute_url(), "/imoveis/", "/", "/sitemap.xml"):
        body = client.get(url).content.decode()
        for secret in secrets:
            assert secret not in body, (url, secret)


def test_feature_flag_hides_people_modules(settings, login):
    settings.SITE_FEATURES = ["brokers"]
    client = login(make_user(roles.ADMIN, username="adm"))
    assert client.get(reverse("admin:people_broker_changelist")).status_code == 200
    assert client.get(reverse("admin:people_partner_changelist")).status_code == 403
    html = client.get(reverse("admin:properties_property_add")).content.decode()
    assert 'name="broker"' in html and 'name="partner"' not in html


def test_person_page_lists_linked_properties(admin_client):
    broker = Broker.objects.create(name="Lista")
    prop = PropertyFactory(broker=broker)
    r = admin_client.get(reverse("admin:people_broker_change", args=[broker.pk]))
    assert prop.code in r.content.decode()
