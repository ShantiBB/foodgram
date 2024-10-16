from django.db.models import manager, Count, Prefetch


class FollowQuerySet(manager.QuerySet):
    def get_follower(self, follower):
        return self.filter(followings__follower=follower)

    def get_recipes(self, model):
        return self.annotate(
            recipes_count=Count('recipes', distinct=True)
        ).prefetch_related(
            Prefetch(
                'recipes',
                queryset=model.objects.all(),
                to_attr='prefetched_recipes'
            )
        )


class UserFollowManager(manager.Manager):
    def get_queryset(self):
        return FollowQuerySet(self.model, using=self._db)

    def get_follower(self, follower):
        return self.get_queryset().get_follower(follower)

    def get_recipes(self, model):
        return self.get_queryset().get_recipes(model)
