from odoo import models, fields, api, _
import logging


# Attendance creation model
class Attendance(models.Model):
    _name = 'se.attendance.management.system'
    _description = 'Track attendance with automated system'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sequence = fields.Char(strign='Reference', required=True, index=True, copy=False, default="NEW")

    attendance_date = fields.Date(string='Date:', default=fields.Date.today())
    name = fields.Many2one(comodel_name='se.subject', string="Course Name")
    program_id = fields.Many2one(comodel_name='se.program')
    semester_id = fields.Many2one(comodel_name='se.semester')
    semester = fields.Char(string="Semester")
    section = fields.Char(string="Section")
    total_student = fields.Integer(string="Total Student")
    total_present_student = fields.Integer(string="Present")
    total_absent_student = fields.Integer(string="Absent")
    progress = fields.Float()
    progress_string = fields.Char(string="Percentage")
    classroom = fields.Char(string="Class Room")
    student_name = fields.Char(string="Student Name")
    batch_id = fields.Many2one(comodel_name='se.batch')
    student_attendance_line_ids = fields.One2many(comodel_name="student.attendance.line",
                                                  inverse_name="attendance_id")
    time_slot = fields.Selection([
        ('8:30 - 9:30', '8:30 - 9:30'),
        ('9:30 - 10-30', '9:30 - 10-30'),
        ('10:30 - 11:30', '10:30 - 11:30'),
        ('11:30 - 12:30', '11:30 - 12:30'),
        ('12:30 - 1:30', '12:30 - 1:30'),
        ('1:30 - 2:30', '1:30 - 2:30'),
        ('2:30 - 3:30', '2:30 - 3:30'),
        ('3:30 - 4:30', '3:30 - 4:30'),
        ('4:30 - 5:30', '4:30 - 5:30'),
    ], string='Select Slot')

    active = fields.Boolean(string='Active:', default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('start', 'Start'),
        ('done', 'Confirm'),
        ('cancel', 'Cancelled'),
    ], default='draft', string='Status')

    def action_confirm(self):
        self.state = 'confirm'

    def action_done(self):
        self.state = 'done'

    def action_draft(self):
        self.state = 'draft'

    def action_cancel(self):
        self.state = 'cancel'

    # Sequence
    @api.model
    def create(self, vals):
        if vals.get('sequence', _('NEW')) == "NEW":
            vals['sequence'] = self.env['ir.sequence'].next_by_code('se.attendance.management.system') or "NEW"
        result = super(Attendance, self).create(vals)
        logging.info(vals['sequence'])
        return result

    @api.onchange('batch_id')
    def _onchange_batch(self):
        for rec in self:
            if self.batch_id:
                total_student = self.env['se.batch'].sudo().search([(
                    'id', '=', rec.batch_id.id
                )])
                total_student = len(total_student.student_ids)
                rec.total_student = total_student


    @api.model
    def create(self, vals):
        rec = super(Attendance, self).create(vals)
        return rec

    def generate_students(self):
        batch_id = self.batch_id
        if batch_id:
            line = self.env['se.batch'].sudo().browse(batch_id.id)
            if line:
                if line.student_ids:
                    student_list = []
                    for student in line.student_ids:
                        student_list.append({
                            'attendance_id': self.id,
                            'batch_id': self.batch_id.id,
                            'name': student.name,
                            'student_id_string': student.student_id_string,
                        })
                    if student_list:
                        student_line = self.env['student.attendance.line'].search([(
                            'attendance_id', '=', self.id,
                        )])
                        for student in student_line:
                            student.unlink()

                        self.env['student.attendance.line'].sudo().create(student_list)
                        self.state = 'start'
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    }

    def submit_attendance(self):
        present_student = self.env['student.attendance.line'].sudo().search([(
            'attendance_id', '=', self.id,
        )])

        for rec in self:
            if self.batch_id:
                total_student = self.env['se.batch'].sudo().search([(
                    'id', '=', rec.batch_id.id
                )])
                total_student = len(total_student.student_ids)
                rec.total_student = total_student

        total_present_student = 0
        for student in present_student:
            if student['attendance'] == True:
                total_present_student += 1
        self.total_present_student = total_present_student
        total_absent_student = total_student - total_present_student
        self.total_absent_student = total_absent_student
        progress = (total_present_student / total_student) * 100
        self.progress_string = f"{progress}%"
        self.state = 'done'


class StudentAttendanceLine(models.Model):
    _name = 'student.attendance.line'
    _description = 'StudentAttendanceLine'

    batch_id = fields.Many2one(comodel_name='se.batch')
    attendance_id = fields.Many2one(comodel_name='se.attendance.management.system')
    student_id = fields.Many2one(comodel_name='se.student', )
    name = fields.Char()
    student_id_string = fields.Char()
    attendance = fields.Boolean()

    @api.model
    def create(self, vals):
        res = super(StudentAttendanceLine, self).create(vals)
        student = self.env['se.attendance.management.system'].sudo().search([(
            'id', '=', self.batch_id.id,
        )], limit=1)
        self.env['student.attendance.line'].write({
            'attendance_id': student.id,
        })
        return res
