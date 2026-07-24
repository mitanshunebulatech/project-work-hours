import { useEffect, useRef, useState } from 'react'
import {
  getProfile, updateProfile, getDepartments, uploadMyProfilePicture, getMyProfilePicture,
  getMyIdentityDocuments, uploadMyIdentityDocument, deleteMyIdentityDocument,
} from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Card, CardContent, CardHeader, CardTitle, Badge, Label, Select, SelectTrigger, SelectValue, SelectContent, SelectItem, Textarea } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { UserAvatar } from '@/components/ui/avatar'
import { EmptyState } from '@/components/ui/empty-state'
import { UserCircle, Save, Camera, FileText, Trash2, Upload } from 'lucide-react'
import { formatDate } from '@/lib/utils'

const DOCUMENT_TYPES = [
  { value: 'PAN', label: 'PAN' },
  { value: 'AADHAAR', label: 'Aadhaar' },
  { value: 'PASSPORT', label: 'Passport' },
  { value: 'OTHER', label: 'Other' },
]

export default function Profile() {
  const { toast } = useToast()
  const [profile, setProfile] = useState<any>(null)
  const [departments, setDepartments] = useState<any[]>([])
  const [documents, setDocuments] = useState<any[]>([])
  const [pictureUrl, setPictureUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [uploadingPicture, setUploadingPicture] = useState(false)
  const [form, setForm] = useState({
    phone_number: '', emergency_contact_phone: '', present_address: '',
    years_of_experience: '', date_of_birth: '', pan_number: '',
  })
  const [errors, setErrors] = useState<any>({})

  const pictureInputRef = useRef<HTMLInputElement>(null)

  // Identity document upload sub-form
  const [docType, setDocType] = useState('')
  const [docNumber, setDocNumber] = useState('')
  const [docFile, setDocFile] = useState<File | null>(null)
  const [uploadingDoc, setUploadingDoc] = useState(false)
  const docFileInputRef = useRef<HTMLInputElement>(null)

  const errMsg = (err: any, fallback: string) => {
    const detail = err.response?.data?.detail
    if (Array.isArray(detail)) return detail[0]?.msg || fallback
    return detail || fallback
  }

  const load = async () => {
    setLoading(true)
    try {
      const [profileRes, deptsRes] = await Promise.all([
        getProfile(),
        getDepartments({ page: 1, size: 100 }),
      ])
      setProfile(profileRes.data)
      setDepartments(deptsRes.data.items)
      setForm({
        phone_number: profileRes.data.phone_number || '',
        emergency_contact_phone: profileRes.data.emergency_contact_phone || '',
        present_address: profileRes.data.present_address || '',
        years_of_experience: profileRes.data.years_of_experience != null ? String(profileRes.data.years_of_experience) : '',
        date_of_birth: profileRes.data.date_of_birth || '',
        pan_number: '', // write-only — the API only ever returns a masked value, never the real one
      })
      // Identity documents require an existing profile row — same guard the
      // backend itself uses (404 "no profile yet" otherwise), so only fetch
      // when we know a profile exists.
      if (profileRes.data.full_name) {
        try {
          const docsRes = await getMyIdentityDocuments()
          setDocuments(docsRes.data)
        } catch {
          setDocuments([])
        }
      }

      // Picture is a separate blob fetch (protected endpoint, <img src>
      // can't carry the auth header) — only bother if one's actually set.
      setPictureUrl(prev => { if (prev) URL.revokeObjectURL(prev); return null })
      if (profileRes.data.profile_picture_path) {
        try {
          const picRes = await getMyProfilePicture()
          setPictureUrl(URL.createObjectURL(picRes.data))
        } catch {
          // No picture yet, or failed to load — UserAvatar falls back to initials.
        }
      }
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])
  useEffect(() => () => { if (pictureUrl) URL.revokeObjectURL(pictureUrl) }, [pictureUrl])

  const validate = () => {
    const e: any = {}
    if (form.pan_number && !/^[A-Za-z]{5}[0-9]{4}[A-Za-z]$/.test(form.pan_number.trim()))
      e.pan_number = 'Format: AAAAA9999A (5 letters, 4 digits, 1 letter)'
    if (form.years_of_experience && (isNaN(Number(form.years_of_experience)) || Number(form.years_of_experience) < 0))
      e.years_of_experience = 'Must be a positive number'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSave = async () => {
    if (!validate()) return
    setSaving(true)
    try {
      await updateProfile({
        phone_number: form.phone_number || null,
        emergency_contact_phone: form.emergency_contact_phone || null,
        present_address: form.present_address || null,
        years_of_experience: form.years_of_experience ? Number(form.years_of_experience) : null,
        date_of_birth: form.date_of_birth || null,
        ...(form.pan_number ? { pan_number: form.pan_number.trim().toUpperCase() } : {}),
      })
      toast('Profile updated')
      load()
    } catch (err: any) {
      toast(errMsg(err, 'Failed to update profile'), 'error')
    } finally { setSaving(false) }
  }

  const handlePictureChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadingPicture(true)
    try {
      await uploadMyProfilePicture(file)
      toast('Profile picture updated')
      load()
    } catch (err: any) {
      toast(errMsg(err, 'Failed to upload picture'), 'error')
    } finally {
      setUploadingPicture(false)
      e.target.value = ''
    }
  }

  const handleDocFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) setDocFile(file)
  }

  const handleUploadDocument = async () => {
    if (!docType) { toast('Select a document type', 'error'); return }
    if (!docFile) { toast('Choose a file to upload', 'error'); return }
    setUploadingDoc(true)
    try {
      await uploadMyIdentityDocument(docType, docNumber || null, docFile)
      toast('Document uploaded')
      setDocType(''); setDocNumber(''); setDocFile(null)
      if (docFileInputRef.current) docFileInputRef.current.value = ''
      load()
    } catch (err: any) {
      toast(errMsg(err, 'Failed to upload document'), 'error')
    } finally { setUploadingDoc(false) }
  }

  const handleDeleteDocument = async (id: number) => {
    try {
      await deleteMyIdentityDocument(id)
      toast('Document removed')
      setDocuments(prev => prev.filter(d => d.id !== id))
    } catch (err: any) {
      toast(errMsg(err, 'Failed to remove document'), 'error')
    }
  }

  const departmentName = (id: number | null) => departments.find(d => d.id === id)?.name

  if (loading) {
    return (
      <div className="p-8 max-w-2xl">
        <div className="h-8 w-40 bg-muted rounded animate-pulse mb-6" />
        <div className="h-64 bg-muted rounded-xl animate-pulse" />
      </div>
    )
  }

  // A user account can exist before HR has created an EmployeeProfile row for
  // them (Sprint 2, FR-E08) — that's a normal state, not an error, so this
  // isn't a blocking screen. Self-service fields (incl. picture/documents)
  // still can't be saved until a profile exists — onboarding is
  // admin-initiated via Admin → Employees.
  const hasProfile = profile?.full_name !== null && profile?.full_name !== undefined

  return (
    <div className="p-8 max-w-2xl">
      <div className="flex items-center gap-4 mb-6">
        <div className="relative group">
          <UserAvatar name={profile?.full_name || profile?.username} src={pictureUrl} size={48} />
          {hasProfile && (
            <>
              <button
                type="button"
                onClick={() => pictureInputRef.current?.click()}
                disabled={uploadingPicture}
                className="absolute inset-0 flex items-center justify-center rounded-full bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity"
                title="Change profile picture"
              >
                <Camera size={16} className="text-white" />
              </button>
              <input
                ref={pictureInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="hidden"
                onChange={handlePictureChange}
              />
            </>
          )}
        </div>
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">
            {profile?.full_name || profile?.username}
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {profile?.username} · <span className="capitalize">{profile?.role}</span>
            {profile?.employee_code && <> · {profile.employee_code}</>}
          </p>
        </div>
      </div>

      {!hasProfile ? (
        <Card>
          <EmptyState
            icon={UserCircle}
            title="No employee profile yet"
            description="HR hasn't set up your employee profile yet — department, designation, and other details will appear here once it's created."
          />
        </Card>
      ) : (
        <>
          <Card className="mb-4">
            <CardHeader className="pb-3"><CardTitle>Organization Details</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Employee ID</p>
                <p className="text-sm text-foreground">{profile?.employee_code || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Department</p>
                <p className="text-sm text-foreground">{departmentName(profile?.department_id) || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Designation</p>
                <p className="text-sm text-foreground">{profile?.designation || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Date of Joining</p>
                <p className="text-sm text-foreground">{profile?.date_of_joining ? formatDate(profile.date_of_joining) : '—'}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">PAN</p>
                {profile?.pan_number_masked
                  ? <Badge variant="outline">{profile.pan_number_masked}</Badge>
                  : <p className="text-sm text-muted-foreground">Not set</p>}
              </div>
              <p className="col-span-2 text-xs text-muted-foreground/70 -mt-2">
                Managed by HR/admin — contact an administrator to change these.
              </p>
            </CardContent>
          </Card>

          <Card className="mb-4">
            <CardHeader className="pb-3"><CardTitle>Personal Details</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label>Phone Number</Label>
                  <Input value={form.phone_number} onChange={e => setForm(f => ({ ...f, phone_number: e.target.value }))} />
                </div>
                <div className="space-y-1.5">
                  <Label>Emergency Contact</Label>
                  <Input value={form.emergency_contact_phone} onChange={e => setForm(f => ({ ...f, emergency_contact_phone: e.target.value }))} />
                </div>
                <div className="space-y-1.5">
                  <Label>Date of Birth</Label>
                  <Input type="date" value={form.date_of_birth} onChange={e => setForm(f => ({ ...f, date_of_birth: e.target.value }))} />
                </div>
                <div className="space-y-1.5">
                  <Label>Years of Experience</Label>
                  <Input type="number" min="0" step="0.5" value={form.years_of_experience}
                    onChange={e => setForm(f => ({ ...f, years_of_experience: e.target.value }))} />
                  {errors.years_of_experience && <p className="text-xs text-destructive">{errors.years_of_experience}</p>}
                </div>
                <div className="space-y-1.5 col-span-2">
                  <Label>Present Address</Label>
                  <Textarea rows={2} value={form.present_address}
                    onChange={e => setForm(f => ({ ...f, present_address: e.target.value }))} />
                </div>
                <div className="space-y-1.5 col-span-2">
                  <Label>PAN <span className="text-muted-foreground font-normal">(leave blank to keep unchanged)</span></Label>
                  <Input placeholder="AAAAA9999A" value={form.pan_number}
                    onChange={e => setForm(f => ({ ...f, pan_number: e.target.value.toUpperCase() }))} />
                  {errors.pan_number && <p className="text-xs text-destructive">{errors.pan_number}</p>}
                  <p className="text-xs text-muted-foreground/70">
                    Every change is logged for compliance — the previous value is never shown again once saved.
                  </p>
                </div>
              </div>
              <Button size="sm" onClick={handleSave} loading={saving}>
                <Save size={14} /> Save Changes
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3"><CardTitle>Identity Documents</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {documents.length === 0 ? (
                <p className="text-sm text-muted-foreground">No identity documents uploaded yet.</p>
              ) : (
                <div className="space-y-2">
                  {documents.map((d: any) => (
                    <div key={d.id} className="flex items-center justify-between rounded-lg border px-3 py-2">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <FileText size={15} className="text-muted-foreground shrink-0" />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-foreground">{d.document_type}</p>
                          <p className="text-xs text-muted-foreground truncate">
                            {d.document_number_masked || 'No number recorded'}
                          </p>
                        </div>
                      </div>
                      <button onClick={() => handleDeleteDocument(d.id)} className="text-muted-foreground hover:text-destructive transition-colors shrink-0" title="Remove">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div className="pt-2 border-t">
                <p className="text-xs font-medium text-muted-foreground mb-2">Upload a new document</p>
                <div className="flex flex-wrap items-end gap-2">
                  <div className="space-y-1.5 w-36">
                    <Label className="text-xs">Type</Label>
                    <Select value={docType} onValueChange={setDocType}>
                      <SelectTrigger><SelectValue placeholder="Select…" /></SelectTrigger>
                      <SelectContent>
                        {DOCUMENT_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5 flex-1 min-w-[140px]">
                    <Label className="text-xs">Document Number (optional)</Label>
                    <Input value={docNumber} onChange={e => setDocNumber(e.target.value)} />
                  </div>
                  <Button type="button" size="sm" variant="outline" onClick={() => docFileInputRef.current?.click()}>
                    <Upload size={13} /> {docFile ? docFile.name.slice(0, 16) : 'Choose file'}
                  </Button>
                  <input
                    ref={docFileInputRef}
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    className="hidden"
                    onChange={handleDocFileChange}
                  />
                  <Button size="sm" onClick={handleUploadDocument} loading={uploadingDoc}>Upload</Button>
                </div>
                <p className="text-xs text-muted-foreground/70 mt-1.5">PDF, JPG, or PNG.</p>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
