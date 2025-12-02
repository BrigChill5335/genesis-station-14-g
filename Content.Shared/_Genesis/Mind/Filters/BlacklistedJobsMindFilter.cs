using System.Linq;
using Content.Shared.Mind.Components;
using Content.Shared.Roles;
using Content.Shared.Roles.Jobs;
using Robust.Shared.Prototypes;

namespace Content.Shared.Mind.Filters;

/// <summary>
/// Replacement for removed MindFilter.
/// Works exactly like the original BlacklistedJobsMindFilter.
/// </summary>
public sealed partial class BlacklistedJobsMindFilter
{
    /// <summary>
    /// List of jobs that disqualify the mind.
    /// </summary>
    [DataField]
    public List<ProtoId<JobPrototype>> Blacklist = new();

    /// <summary>
    /// Equivalent to the old ShouldRemove().
    /// Returns true if the mind *should be removed*.
    /// </summary>
    public bool ShouldRemove(Entity<MindComponent> mind, IEntityManager entMan)
    {
        var jobSys = entMan.System<SharedJobSystem>();
        return !Blacklist.Any(job => jobSys.MindHasJobWithId(mind, job));
    }

    /// <summary>
    /// Inverse of ShouldRemove — checks if the mind is allowed.
    /// </summary>
    public bool IsAllowed(Entity<MindComponent> mind, IEntityManager entMan)
        => !ShouldRemove(mind, entMan);
}
